"""Bounded, CPU-only appearance memory for one selected animal.

Sparse ORB correspondence handles rotations and partial pose changes. A small
foreground histogram handles non-rigid poses, but requires matching fur features
and repeated confirmation by RegionTracker. Anatomy is never learned from a
foreground silhouette. A new interior surface can only supply samples to the
separate conservative temporal periodicity check.
"""
import math


class AppearanceRecovery:
    def __init__(self, cv, np):
        self.cv, self.np = cv, np
        self.orb = cv.ORB_create(nfeatures=240, nlevels=3, edgeThreshold=8,
                                 patchSize=21, fastThreshold=8)
        self.matcher = cv.BFMatcher(cv.NORM_HAMMING)
        self.references = []
        self.last_remembered = None
        self.exclusions = []
        self.scene_background = None
        self.scene_mask = None

    @staticmethod
    def _inside(points, box):
        x,y,w,h = box
        return ((points[:,0]>=x)&(points[:,0]<=x+w)&
                (points[:,1]>=y)&(points[:,1]<=y+h))

    def _patch(self, gray, box):
        x,y,w,h = [int(round(v)) for v in box]
        return gray[max(0,y):max(0,y+h),max(0,x):max(0,x+w)]

    def remember(self, gray, boxes, now, force=False):
        if not force and self.last_remembered is not None and now-self.last_remembered<5:
            return
        self.last_remembered=now
        cv,np = self.cv,self.np
        self.orb.setMaxFeatures(240)
        x,y,w,h = boxes['animal']; height,width = gray.shape
        mask=np.zeros_like(gray)
        mx,my=max(2,int(w*.15)),max(2,int(h*.15))
        mask[int(y)+my:int(y+h)-my,int(x)+mx:int(x+w)-mx]=255
        if self.scene_mask is not None:
            mask=cv.bitwise_and(mask,self.scene_mask)
        keys,desc=self.orb.detectAndCompute(gray,mask)
        if desc is None or len(keys)<8:
            return
        points=np.array([k.pt for k in keys],dtype=np.float32)
        animal=self._patch(gray,boxes['animal'])
        # Learn contrast against a local ring, not against the entire enclosure.
        margin=max(8,int(max(w,h)*.2))
        ring=np.zeros_like(gray)
        ring[max(0,int(y)-margin):min(height,int(y+h)+margin),
             max(0,int(x)-margin):min(width,int(x+w)+margin)]=255
        ring[int(y):int(y+h),int(x):int(x+w)]=0
        chest=boxes.get('respiration')
        patch=self._patch(gray,chest) if chest else None
        # The selected torso is a cleaner fur sample than the full bounding
        # rectangle, which can contain a substantial amount of white bedding.
        seed=patch if patch is not None and patch.size else animal
        ah=cv.calcHist([seed],[0],None,[32],[0,256]).ravel()+1
        bh=cv.calcHist([gray],[0],ring,[32],[0,256]).ravel()+1
        ah/=ah.sum();bh/=bh.sum()
        posterior=ah/(ah+bh)
        if chest is None and self.references:
            # A coarse pose box can contain bedding. Do not teach it that the
            # bedding is fur; inherit the last verified torso's photometry.
            verified=next((r for r in reversed(self.references) if r['chest'] is not None),self.references[0])
            ah=verified['hist'].copy();posterior=verified['posterior'].copy()
        ref={'points':points,'descriptors':desc,'boxes':dict(boxes),
             'hist':ah,'posterior':posterior,
             'lookup':np.repeat((posterior>=.62).astype(np.uint8)*255,8),
             'chest':cv.resize(patch,(32,32)) if patch is not None and patch.size else None}
        if not self.references:
            self.references.append(ref)
        else:
            # Keep the first anatomical reference and only two recent views.
            self.references.append(ref)
            if len(self.references)>3:self.references.pop(1)

    def _transform_box(self, box, matrix, shape):
        np=self.np;x,y,w,h=box
        corners=np.array([[x,y,1],[x+w,y,1],[x,y+h,1],[x+w,y+h,1]]) @ matrix.T
        low=corners.min(axis=0);high=corners.max(axis=0)
        if low[0]<0 or low[1]<0 or high[0]>shape[1] or high[1]>shape[0]:return None
        return (float(low[0]),float(low[1]),float(high[0]-low[0]),float(high[1]-low[1]))

    def _geometric(self, gray, ref, src, dst):
        cv,np=self.cv,self.np
        if len(src)<8:return None
        matrix,inliers=cv.estimateAffinePartial2D(src,dst,method=cv.RANSAC,
                                ransacReprojThreshold=2.0,maxIters=500,confidence=.99)
        if matrix is None or inliers is None:return None
        good=inliers.ravel().astype(bool); count=int(good.sum())
        support=count/len(src)
        if count<8 or support<.7 or not np.isfinite(matrix).all():return None
        scale=math.hypot(matrix[0,0],matrix[1,0])
        if not .5<=scale<=1.8:return None
        source=src[good]; original=ref['boxes']['animal']
        extent=np.ptp(source,axis=0)
        if extent[0]<original[2]*.25 or extent[1]<original[3]*.2:return None
        body=self._transform_box(original,matrix,gray.shape)
        if body is None:return None
        boxes={'animal':body};chest=ref['boxes'].get('respiration')
        if chest and ref['chest'] is not None:
            x,y,w,h=chest
            nearby=(x-w*.25,y-h*.25,w*1.5,h*1.5)
            # Several matched points near the original torso plus an aligned
            # appearance check are required before transferring respiration.
            if int(self._inside(source,nearby).sum())>=3:
                mapping=matrix.copy()
                mapping[:,2]+=matrix[:,:2] @ np.array([x,y])
                aligned=cv.warpAffine(gray,mapping,(max(1,round(w)),max(1,round(h))),
                                      flags=cv.INTER_LINEAR|cv.WARP_INVERSE_MAP)
                correlation=float(cv.matchTemplate(cv.resize(aligned,(32,32)),
                                  ref['chest'],cv.TM_CCOEFF_NORMED)[0,0])
                mapped=self._transform_box(chest,matrix,gray.shape)
                if mapped and math.isfinite(correlation) and correlation>=.8 and support>=.8:
                    boxes['respiration']=mapped
        return {'boxes':boxes,'confidence':min(.98,support),'kind':'features'}

    def _foreground(self, gray, ref, matched_points, motion=None):
        cv,np=self.cv,self.np
        if len(matched_points)<4 and motion is None:return []
        mask=(self.scene_mask.copy() if self.scene_mask is not None else
              cv.LUT(cv.GaussianBlur(gray,(3,3),0),ref['lookup']))
        height,width=gray.shape
        border_x,border_y=max(2,int(width*.08)),max(2,int(height*.08))
        mask[:border_y]=0;mask[-border_y:]=0;mask[:,:border_x]=0;mask[:,-border_x:]=0
        for b in self.exclusions:
            x,y,w,h=b
            mask[max(0,int(y*height)):min(height,int((y+h)*height)),
                 max(0,int(x*width)):min(width,int((x+w)*width))]=0
        if motion is not None:
            # Keep a small margin around changed pixels. Unchanged dark rails
            # and enclosure shadows must not join a newly posed animal.
            nearby=cv.dilate(motion,np.ones((11,11),np.uint8))
            mask=cv.bitwise_and(mask,nearby)
        original=ref['boxes']['animal']
        # Dark enclosure rails often join the animal's silhouette. Remove only
        # runs longer than the learned body before grouping foreground pixels.
        if motion is None:
            horizontal=cv.morphologyEx(mask,cv.MORPH_OPEN,np.ones((1,max(48,int(original[2]*1.2))),np.uint8))
            vertical=cv.morphologyEx(mask,cv.MORPH_OPEN,np.ones((max(48,int(original[3]*2)),1),np.uint8))
            mask=cv.subtract(mask,cv.bitwise_or(horizontal,vertical))
        mask=cv.morphologyEx(mask,cv.MORPH_CLOSE,np.ones((5,5),np.uint8))
        proposals=[(0,0,mask)]
        groups=[]
        seeds=matched_points
        if len(seeds)>24:
            cells=(seeds/max(12,max(original[2:])*.25)).astype(np.int32)
            _,indices,counts=np.unique(cells,axis=0,return_index=True,return_counts=True)
            seeds=seeds[indices[np.argsort(counts)[::-1][:24]]]
        for point in seeds:
            nearby=matched_points[np.linalg.norm(matched_points-point,axis=1)<max(original[2:])*.65]
            if len(nearby)<4:continue
            low=nearby.min(axis=0);high=nearby.max(axis=0)
            x1=max(0,int(low[0]-original[2]*.25));x2=min(width,int(high[0]+original[2]*.25))
            y1=max(0,int(low[1]-original[3]*.6));y2=min(height,int(high[1]+original[3]*.6))
            box=(x1,y1,x2-x1,y2-y1)
            if all(self._iou(box,b)<.6 for _,b in groups):groups.append((len(nearby),box))
        # Bound split operations even if many descriptors matched the scene.
        for _,(x,y,w,h) in sorted(groups,reverse=True)[:3]:
            proposals.append((x,y,mask[y:y+h,x:x+w]))
        if motion is not None:
            changed=cv.findContours(motion,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)[-2]
            for contour in sorted(changed,key=cv.contourArea,reverse=True)[:3]:
                x,y,w,h=cv.boundingRect(contour)
                if w*h<original[2]*original[3]*.1:continue
                mx,my=max(3,int(original[2]*.1)),max(3,int(original[3]*.1))
                x1,y1=max(0,x-mx),max(0,y-my);x2,y2=min(width,x+w+mx),min(height,y+h+my)
                proposals.append((x1,y1,mask[y1:y2,x1:x2]))
        area=original[2]*original[3];out=[]
        for ox,oy,proposal in proposals:
            contours=cv.findContours(proposal,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)[-2]
            for contour in contours:
                x,y,w,h=cv.boundingRect(contour);x+=ox;y+=oy
                if not area*.25<=w*h<=area*1.5 or not .3<=w/max(h,1)<=3.5:continue
                if x<=border_x or y<=border_y or x+w>=width-border_x or y+h>=height-border_y:continue
                supported=int(self._inside(matched_points,(x,y,w,h)).sum())
                changed=(cv.countNonZero(motion[y:y+h,x:x+w])/(w*h)) if motion is not None else 0
                if motion is not None and changed<.15:continue
                if (supported<4 and changed<.2) or cv.contourArea(contour)<w*h*.3:continue
                patch=gray[y:y+h,x:x+w]
                hist=cv.calcHist([patch],[0],mask[y:y+h,x:x+w],[32],[0,256]).ravel()+1;hist/=hist.sum()
                # Compare foreground with foreground. The torso reference can
                # include bedding; its full histogram unfairly penalizes a
                # valid fur-only silhouette after a non-rigid pose change.
                expected=ref['hist']*(ref['posterior']>=.62)
                total=float(expected.sum())
                if total<=0:continue
                expected=expected/total
                likeness=float(np.minimum(hist,expected).sum())
                if likeness < (.6 if supported>=4 else .7):continue
                # A silhouette can resume life-cycle tracking, never respiration.
                out.append({'boxes':{'animal':(float(x),float(y),float(w),float(h))},
                            'confidence':min(.85,.65+supported*.015) if supported>=4 else .72,
                            'kind':'foreground' if supported>=4 else 'motion_foreground'})
        return out

    def _correspondences(self, ref, desc, points):
        pairs=self.matcher.knnMatch(ref['descriptors'],desc,k=2)
        ambiguous=[p for p in pairs if len(p)==2 and p[0].distance<=60
                   and p[1].distance<=p[0].distance*1.08
                   and math.dist(points[p[0].trainIdx],points[p[1].trainIdx])
                   >max(ref['boxes']['animal'][2:])*.75]
        alternatives=self.np.empty((0,2),self.np.float32)
        if len(ambiguous)>=8:
            alternatives=self.np.unique(self.np.array(
                [points[m.trainIdx] for pair in ambiguous for m in pair],self.np.float32),axis=0)
        matches=[p[0] for p in pairs if len(p)==2 and p[0].distance<.8*p[1].distance
                 and p[0].distance<=60]
        unique={}
        for m in matches:
            if m.trainIdx not in unique or m.distance<unique[m.trainIdx].distance:unique[m.trainIdx]=m
        matches=list(unique.values())
        return (self.np.array([ref['points'][m.queryIdx] for m in matches],dtype=self.np.float32),
                self.np.array([points[m.trainIdx] for m in matches],dtype=self.np.float32),alternatives)

    def find(self, gray, previous=None, anatomy_only=False):
        if not self.references:return None
        cv,np=self.cv,self.np
        motion=None
        if previous is not None and previous.shape==gray.shape:
            motion=cv.threshold(cv.absdiff(previous,gray),24,255,cv.THRESH_BINARY)[1]
            if cv.countNonZero(motion)>gray.size*.45:
                motion=None  # Global illumination/scene changes are not an animal cue.
            else:
                motion=cv.morphologyEx(motion,cv.MORPH_CLOSE,np.ones((5,5),np.uint8))
        mask=np.zeros_like(gray);height,width=gray.shape
        bx,by=max(2,int(width*.08)),max(2,int(height*.08))
        mask[by:height-by,bx:width-bx]=255
        for x,y,w,h in self.exclusions:
            mask[max(0,int(y*height)):min(height,int((y+h)*height)),
                 max(0,int(x*width)):min(width,int((x+w)*width))]=0
        self.orb.setMaxFeatures(400)
        keys,desc=self.orb.detectAndCompute(gray,mask)
        points=np.array([k.pt for k in keys],dtype=np.float32);candidates=[]
        for ref in self.references:
            if anatomy_only and ref['chest'] is None:continue
            if desc is None or len(keys)<8:
                if not anatomy_only:
                    candidates.extend(self._foreground(gray,ref,np.empty((0,2),np.float32),motion))
                continue
            src,dst,alternatives=self._correspondences(ref,desc,points)
            supported=np.unique(np.concatenate([dst.reshape(-1,2),alternatives]),axis=0)
            if len(src)<4:
                if not anatomy_only:candidates.extend(self._foreground(gray,ref,supported,motion))
                continue
            geometric=self._geometric(gray,ref,src,dst)
            if geometric:
                candidates.append(geometric)
                outside=~self._inside(points,geometric['boxes']['animal'])
                if int(outside.sum())>=8:
                    alternate_src,alternate_dst,_=self._correspondences(ref,desc[outside],points[outside])
                    alternate=self._geometric(gray,ref,alternate_src,alternate_dst)
                    if alternate:candidates.append(alternate)
            if not anatomy_only:candidates.extend(self._foreground(gray,ref,supported,motion))
        candidates.sort(key=lambda c:(c['confidence'], 'respiration' in c['boxes']),reverse=True)
        if not candidates and not anatomy_only:
            candidates = self._stationary_candidates(gray, mask)
            candidates.sort(key=lambda c: c['confidence'], reverse=True)
        if not candidates:return None
        best=candidates[0]
        # Strong support for two separated animals/objects is ambiguous.
        for other in candidates[1:]:
            if self._iou(best['boxes']['animal'],other['boxes']['animal'])<.2 and other['confidence']>=best['confidence']-.08:
                return None
        if 'respiration' not in best['boxes']:
            anatomical=[c for c in candidates if 'respiration' in c['boxes']
                        and c['confidence']>=.8
                        and self._iou(best['boxes']['animal'],c['boxes']['animal'])>=.5]
            if anatomical:
                # A perfect recent body-only view must not hide a slightly
                # weaker, independently verified torso correspondence.
                best=max(anatomical,key=lambda c:c['confidence'])
        if anatomy_only and 'respiration' not in best['boxes']:return None
        return best

    def _stationary_candidates(self, gray, allowed_mask):
        """Recheck an unchanged pose without enclosure features crowding out fur.

        This bounded fallback requires distributed descriptor matches at their
        reference positions and the normal RANSAC thresholds. It never transfers
        a chest region; that still needs independent correspondence.
        """
        cv, np = self.cv, self.np
        mask = np.zeros_like(gray)
        for ref in self.references:
            x, y, w, h = map(round, ref['boxes']['animal'])
            mask[y:y+h, x:x+w] = allowed_mask[y:y+h, x:x+w]
        keys, desc = self.orb.detectAndCompute(gray, mask)
        if desc is None or len(keys) < 8:
            return []
        points = np.array([key.pt for key in keys], dtype=np.float32)
        candidates = []
        for ref in self.references:
            src, dst, _ = self._correspondences(ref, desc, points)
            if len(src) < 8:
                continue
            stationary = np.linalg.norm(dst-src, axis=1) <= 3.0
            candidate = self._geometric(gray, ref, src[stationary], dst[stationary])
            if candidate is not None:
                candidate['boxes'].pop('respiration', None)
                candidate['confidence'] = min(.9, candidate['confidence'])
                candidate['kind'] = 'stationary_features'
                candidates.append(candidate)
        return candidates

    def observe_scene(self, gray):
        """Learn uncovered bedding at 1 Hz without absorbing a stationary animal.

        The selected animal is darker than its local bedding in this mode.
        Brightening can reveal background; darkening cannot overwrite it.
        A global exposure shift is removed using the scene median.
        """
        cv,np=self.cv,self.np
        if self.scene_background is None:
            self.scene_background=gray.copy()
        background=self.scene_background
        offset=float(np.median(gray.astype(np.int16)-background.astype(np.int16)))
        normalized=np.clip(gray.astype(np.float32)-offset,0,255).astype(np.uint8)
        delta=background.astype(np.int16)-normalized.astype(np.int16)
        mask=(delta>28).astype(np.uint8)*255
        mask=cv.morphologyEx(mask,cv.MORPH_OPEN,np.ones((3,3),np.uint8))
        self.scene_mask=cv.morphologyEx(mask,cv.MORPH_CLOSE,np.ones((5,5),np.uint8))
        self.scene_background=np.maximum(background,normalized)

    def find_surface(self, gray, animal):
        """Find an interior textured surface, for periodicity testing only."""
        if self.scene_mask is None:return None
        cv,np=self.cv,self.np
        x,y,w,h=map(round,animal)
        patch=gray[y:y+h,x:x+w];mask=self.scene_mask[y:y+h,x:x+w]
        if not patch.size or mask.shape!=patch.shape:return None
        padded=cv.copyMakeBorder(mask,1,1,1,1,cv.BORDER_CONSTANT,value=0)
        distances=cv.distanceTransform(padded,cv.DIST_L2,3)[1:-1,1:-1]
        _,radius,_,point=cv.minMaxLoc(distances)
        if radius<10:return None
        pw,ph=max(12,min(40,round(radius*1.2))),max(12,min(32,round(radius)))
        px=max(0,min(w-pw,point[0]-pw//2));py=max(0,min(h-ph,point[1]-ph//2))
        region=patch[py:py+ph,px:px+pw];inside=mask[py:py+ph,px:px+pw]
        if (region.size<120 or float(region.std())<8 or
                cv.countNonZero(inside)<inside.size*.95):return None
        return (float(x+px),float(y+py),float(pw),float(ph))

    def find_chest_features(self, gray, animal):
        """Fit only the verified torso, independently of non-rigid head/legs."""
        cv,np=self.cv,self.np
        x,y,w,h=animal
        mask=np.zeros_like(gray)
        mask[max(0,round(y)):min(gray.shape[0],round(y+h)),
             max(0,round(x)):min(gray.shape[1],round(x+w))]=255
        self.orb.setMaxFeatures(240)
        keys,desc=self.orb.detectAndCompute(gray,mask)
        if desc is None or len(keys)<8:return None
        points=np.array([key.pt for key in keys],np.float32)
        candidates=[]
        for ref in self.references:
            chest=ref['boxes'].get('respiration')
            if chest is None or ref['chest'] is None:continue
            cx,cy,cw,ch=chest
            local=self._inside(ref['points'],(cx-cw*.2,cy-ch*.2,cw*1.4,ch*1.4))
            if int(local.sum())<5:continue
            descriptors=ref['descriptors'][local];source=ref['points'][local]
            pairs=self.matcher.knnMatch(descriptors,desc,k=2)
            matches=[p[0] for p in pairs if len(p)==2 and p[0].distance<.75*p[1].distance and p[0].distance<=45]
            unique={m.trainIdx:m for m in sorted(matches,key=lambda m:-m.distance)}
            matches=list(unique.values())
            if len(matches)<5:continue
            src=np.array([source[m.queryIdx] for m in matches],np.float32)
            dst=np.array([points[m.trainIdx] for m in matches],np.float32)
            matrix,inliers=cv.estimateAffinePartial2D(src,dst,method=cv.RANSAC,
                                  ransacReprojThreshold=1.5,maxIters=300,confidence=.99)
            if matrix is None or inliers is None or not np.isfinite(matrix).all():continue
            good=inliers.ravel().astype(bool)
            if int(good.sum())<5 or float(good.mean())<.8:continue
            spread=np.ptp(src[good],axis=0)
            if spread[0]<cw*.35 or spread[1]<ch*.35:continue
            scale=math.hypot(matrix[0,0],matrix[1,0])
            if not .65<=scale<=1.5:continue
            mapped=self._transform_box(chest,matrix,gray.shape)
            if mapped is None:continue
            mx,my,mw,mh=mapped
            if mx<x or my<y or mx+mw>x+w or my+mh>y+h:continue
            mapping=matrix.copy();mapping[:,2]+=matrix[:,:2]@np.array([cx,cy])
            aligned=cv.warpAffine(gray,mapping,(max(1,round(cw)),max(1,round(ch))),
                                  flags=cv.INTER_LINEAR|cv.WARP_INVERSE_MAP)
            correlation=float(cv.matchTemplate(cv.resize(aligned,(32,32)),ref['chest'],cv.TM_CCOEFF_NORMED)[0,0])
            if math.isfinite(correlation) and correlation>=.85:candidates.append((correlation,mapped))
        candidates.sort(reverse=True)
        if not candidates:return None
        score,box=candidates[0]
        if any(self._iou(box,b)<.3 and other>=score-.08 for other,b in candidates[1:]):return None
        return box

    def find_local_chest(self, gray, animal):
        """Restore a known torso texture inside a separately detected animal.

        A silhouette never creates a new torso. Only a distinctive, previously
        verified patch, including rotations, can transfer the anatomical ROI.
        The caller still requires independent temporal confirmations.
        """
        cv,np=self.cv,self.np
        x,y,w,h=map(lambda v:int(round(v)),animal)
        body=gray[max(0,y):min(gray.shape[0],y+h),max(0,x):min(gray.shape[1],x+w)]
        if not body.size:return None
        candidates=[]
        for ref in self.references:
            if ref['chest'] is None or 'respiration' not in ref['boxes']:continue
            _,_,cw,ch=ref['boxes']['respiration']
            for quarter in range(4):
                source=np.rot90(ref['chest'],quarter).copy()
                rw,rh=(ch,cw) if quarter%2 else (cw,ch)
                for scale in (.8,1.,1.2):
                    tw,th=max(8,round(rw*scale)),max(8,round(rh*scale))
                    if tw>=body.shape[1] or th>=body.shape[0] or tw*th>w*h*.4:continue
                    template=cv.resize(source,(tw,th))
                    if float(template.std())<8:continue
                    scores=cv.matchTemplate(body,template,cv.TM_CCOEFF_NORMED)
                    for _ in range(2):
                        _,score,_,location=cv.minMaxLoc(scores);px,py=location
                        if math.isfinite(score):candidates.append((float(score),(float(x+px),float(y+py),float(tw),float(th))))
                        scores[max(0,py-th//2):min(scores.shape[0],py+th//2+1),
                               max(0,px-tw//2):min(scores.shape[1],px+tw//2+1)]=-1
        candidates.sort(reverse=True)
        if not candidates or candidates[0][0]<.90:return None
        score,box=candidates[0]
        if any(self._iou(box,b)<.3 and other>=score-.08 for other,b in candidates[1:]):return None
        return box

    @staticmethod
    def _iou(a,b):
        x,y,w,h=a;xx,yy,ww,hh=b
        overlap=max(0,min(x+w,xx+ww)-max(x,xx))*max(0,min(y+h,yy+hh)-max(y,yy))
        return overlap/max(1,w*h+ww*hh-overlap)

    def memory_bytes(self):
        references=sum(value.nbytes for ref in self.references for value in ref.values()
                       if isinstance(value,self.np.ndarray))
        return references+sum(value.nbytes for value in (self.scene_background,self.scene_mask)
                              if isinstance(value,self.np.ndarray))
