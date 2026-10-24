"""Local optical flow with bounded, automatic recovery across animal poses.

Appearance memory can restore life-cycle tracking independently of the selected
torso correspondence required to resume respiration.
"""
import math
from .appearance_recovery import AppearanceRecovery


class RegionTracker:
    def __init__(self, cv, np):
        self.cv, self.np = cv, np
        self.state = 'unselected'
        self.confidence = 0.0
        self.boxes = {}
        self.previous = None
        self.points = None
        self.template = None
        self.last_ts = None
        self.stable_frames = 0
        self.reason = 'no_selection'
        self.anchor_patch = None
        self.anchor_boxes = {}
        self.search_ts = None
        self.candidate = None
        self.candidate_since = None
        self.candidate_hits = 0
        self.recovery_since = None
        self.feature_ts = None
        self.flow_pixels = 0
        self.initial_boxes = {}
        self.motion_activity = 0.0
        self.recovery = AppearanceRecovery(cv, np)
        self.respiration_ready = False
        self.generation = 0
        self.chest_search_ts = None
        self.recovery_kind = 'selection'
        self.chest_candidate = None
        self.chest_hits = 0
        self.chest_since = None
        self.chest_last_ts = None

    def lose(self, reason):
        self.state = 'lost'
        self.reason = reason
        self.confidence = 0.0
        self.points = None
        self.stable_frames = 0
        self.candidate = None
        self.candidate_hits = 0
        self.candidate_since = None
        self.recovery_since = None
        self.motion_activity = 0.0
        self.respiration_ready = False
        self.chest_candidate = None
        self.chest_hits = 0
        self.chest_since = None
        self.chest_last_ts = None

    def _features(self, gray, box):
        x, y, w, h = box
        margin_x, margin_y = max(2, int(w*.1)), max(2, int(h*.1))
        x1, y1 = max(0, int(x)+margin_x), max(0, int(y)+margin_y)
        crop = gray[y1:int(y+h)-margin_y, x1:int(x+w)-margin_x]
        if not crop.size:
            return None
        points = self.cv.goodFeaturesToTrack(crop, maxCorners=40, qualityLevel=.02,
                                            minDistance=4, blockSize=5)
        if points is not None:
            points += self.np.array([x1, y1], dtype=self.np.float32)
        return points

    def _flow_window(self, gray):
        # Build pyramids around the animal, not around the enclosure and bowls.
        x, y, w, h = self.boxes['animal']
        margin = max(12, int(max(w, h)*.2))
        height, width = gray.shape[:2]
        return (max(0, int(x)-margin), max(0, int(y)-margin),
                min(width, int(math.ceil(x+w))+margin),
                min(height, int(math.ceil(y+h))+margin))

    def _tracking_features(self, gray, boxes):
        # A verified torso is rigid enough for flow; head/leg motion is not.
        # Keep the full body box for framing while anchoring to the torso.
        if 'respiration' in boxes:
            points=self._features(gray,boxes['respiration'])
            if points is not None and len(points)>=12:return points
        return self._features(gray,boxes['animal'])

    def _patch(self, gray, box):
        x,y,w,h = [int(round(v)) for v in box]
        return gray[y:y+h,x:x+w]

    def initialize(self, gray, boxes, now):
        self.generation += 1
        self.initial_boxes = {name:dict(box) for name,box in boxes.items()}
        self.anchor_patch = None
        self.anchor_boxes = {}
        self.candidate = None
        self.candidate_hits = 0
        self.candidate_since = None
        height, width = gray.shape[:2]
        self.boxes = {name: (b['x']*width, b['y']*height, b['width']*width, b['height']*height)
                      for name,b in boxes.items()}
        if 'animal' not in self.boxes:
            self.lose('select_animal');return
        patch = self._patch(gray,self.boxes['animal'])
        if patch.size < 120 or float(patch.std()) < 8:
            self.lose('insufficient_texture');return
        self.template = self.cv.resize(patch,(64,64))
        self.anchor_patch = patch.copy()
        self.anchor_boxes = dict(self.boxes)
        self.search_ts = None
        self.recovery_since = None
        self.points = self._tracking_features(gray,self.boxes)
        if self.points is None or len(self.points)<12:
            self.lose('insufficient_features');return
        self.previous = gray.copy()
        self.last_ts = now
        self.feature_ts = now
        self.state = 'acquiring'
        self.reason = 'stabilizing'
        self.stable_frames = 0
        self.motion_activity = 0.0
        self.respiration_ready = 'respiration' in boxes
        self.recovery.remember(gray,self.boxes,now,force=True)

    def update(self, gray, now):
        if self.state == 'unselected':return
        if self.state == 'lost':
            try:
                self._search(gray, now)
            except Exception:
                self.candidate = None
                self.candidate_hits = 0
                self.candidate_since = None
                self.reason = 'search_error'
            return
        if self.last_ts is None or not 0 < now-self.last_ts <= 2:
            self.lose('frame_gap');return
        cv,np = self.cv,self.np
        if gray.shape != self.previous.shape:
            self.lose('frame_size_changed');return
        try:
            if self.state == 'locked' and now-self.last_ts < 1.0:
                # Respiration still samples at 5 Hz. Expensive body flow can
                # wait up to one second only while appearance is nearly exact.
                # Occlusion/pose changes fail this cheap check immediately.
                patch=self._patch(gray,self.boxes['animal'])
                similarity=float(cv.matchTemplate(cv.resize(patch,(64,64)),
                                  self.template,cv.TM_CCOEFF_NORMED)[0,0])
                if math.isfinite(similarity) and similarity >= .98:
                    self.flow_pixels=0
                    self.motion_activity=0.0
                    self._maintain_reference(gray,now)
                    return
            x1,y1,x2,y2 = self._flow_window(gray)
            previous = self.previous[y1:y2,x1:x2]
            current = gray[y1:y2,x1:x2]
            self.flow_pixels = int(current.size)
            origin = np.array([x1,y1], dtype=np.float32)
            local_points = self.points - origin
            nxt, valid, _ = cv.calcOpticalFlowPyrLK(previous,current,local_points,None,
                                                  winSize=(21,21),maxLevel=2)
            if nxt is None: self.lose('flow_failed');return
            back, back_valid, _ = cv.calcOpticalFlowPyrLK(current,previous,nxt,None,
                                                        winSize=(21,21),maxLevel=2)
            if back is None: self.lose('flow_failed');return
            good=(valid.ravel()==1)&(back_valid.ravel()==1)&(np.linalg.norm(back-local_points,axis=2).ravel()<1.0)
            if int(good.sum())<10 or float(good.mean())<.7:
                self.lose('occluded_or_ambiguous');return
            nxt += origin
            matrix,inliers=cv.estimateAffinePartial2D(self.points[good],nxt[good],
                            method=cv.RANSAC,ransacReprojThreshold=1.5)
            if matrix is None or inliers is None or float(inliers.mean())<.75:
                self.lose('inconsistent_motion');return
            scale=math.hypot(matrix[0,0],matrix[1,0])
            angle=abs(math.degrees(math.atan2(matrix[1,0],matrix[0,0])))
            if not .94 <= scale <= 1.06 or angle>4:
                self.lose('pose_changed');return
            # Only translation/scale: reject rotation rather than slide the chest ROI.
            if angle>1.5:
                self.lose('rotation_changed');return
            # Sub-percent flow jitter must not resize the crop every second:
            # changing its dimensions would discard the respiration window.
            if abs(scale-1.0) <= .01:
                scale=1.0
            height,width=gray.shape[:2]; shifted={}
            for name,(x,y,w,h) in self.boxes.items():
                center=matrix @ np.array([x+w/2,y+h/2,1.0])
                nw,nh=w*scale,h*scale
                box=(float(center[0]-nw/2),float(center[1]-nh/2),nw,nh)
                if box[0]<0 or box[1]<0 or box[0]+nw>width or box[1]+nh>height:
                    self.lose('out_of_frame');return
                shifted[name]=box
            old=self.boxes['animal'];new=shifted['animal']
            shift=math.hypot(new[0]-old[0],new[1]-old[1])
            if shift>min(old[2],old[3])*.2:
                self.lose('motion_too_fast');return
            patch=self._patch(gray,new)
            if not patch.size or float(patch.std())<8:
                self.lose('occluded');return
            appearance=float(cv.matchTemplate(cv.resize(patch,(64,64)),self.template,cv.TM_CCOEFF_NORMED)[0,0])
            if not math.isfinite(appearance) or appearance<.65:
                self.lose('appearance_changed');return
            points=nxt[good].reshape(-1,1,2)
            if len(points)<20 or self.feature_ts is None or now-self.feature_ts>=1.0:
                anchors=shifted if self.respiration_ready else {'animal':new}
                points=self._tracking_features(gray,anchors)
                self.feature_ts=now
            if points is None or len(points)<12:
                self.lose('insufficient_features');return
            local_appearance=appearance
            if self.respiration_ready and 'respiration' in shifted:
                before=self._patch(self.previous,self.boxes['respiration'])
                after=self._patch(gray,shifted['respiration'])
                if not before.size or not after.size:
                    self.lose('chest_occluded');return
                local_appearance=float(cv.matchTemplate(cv.resize(after,(32,32)),
                                       cv.resize(before,(32,32)),cv.TM_CCOEFF_NORMED)[0,0])
                if not math.isfinite(local_appearance) or local_appearance<.8:
                    self.lose('chest_appearance_changed');return
            self.confidence=min(float(good.mean()),float(inliers.mean()),max(0.0,local_appearance))
            # Movement is a speed, so the decision must not change with FPS.
            speed=shift/(now-self.last_ts)
            moving=speed>5.0 or abs(scale-1)>.01
            self.motion_activity=min(100.0,100.0*speed/max(min(old[2],old[3]),1)) if moving else 0.0
            self.stable_frames=0 if moving else self.stable_frames+1
            recovery_ready = (self.recovery_since is None or
                              (now - self.recovery_since >= 2.0 and self.stable_frames >= 5))
            if moving and self.recovery_since is not None:
                self.recovery_since = now
            self.state='moving' if moving else ('locked' if self.stable_frames>=3 and recovery_ready else 'acquiring')
            self.reason='animal_moving' if moving else ('stable' if self.state=='locked' else 'stabilizing')
            self.boxes=shifted;self.points=points;self.previous=gray.copy();self.last_ts=now
            self._maintain_reference(gray,now)
        except Exception:
            self.lose('tracking_error')

    def _maintain_reference(self, gray, now):
        if self.state != 'locked' or self.confidence < .9:return
        # Original anatomy remains in the bounded bank, even when a new pose
        # can only support life-cycle tracking.
        boxes={k:v for k,v in self.boxes.items() if k!='respiration' or self.respiration_ready}
        self.recovery.remember(gray,boxes,now)
        if self.respiration_ready or 'respiration' not in self.initial_boxes:return
        if self.chest_search_ts is not None and now-self.chest_search_ts<2:return
        self.chest_search_ts=now
        found=self.recovery.find(gray,anatomy_only=True)
        if (found and 'respiration' in found['boxes'] and
                self._overlap(self.boxes['animal'],found['boxes']['animal'])>=.5 and
                self._confirm_chest(found['boxes']['respiration'],now)):
            self.boxes['respiration']=found['boxes']['respiration']
            self.respiration_ready=True
            self.generation+=1
        elif (not found or 'respiration' not in found['boxes'] or
              self._overlap(self.boxes['animal'],found['boxes']['animal'])<.5):
            self._confirm_chest(None,now)

    def _confirm_chest(self, box, now):
        if box is None:
            self.chest_candidate=None;self.chest_hits=0;self.chest_since=None;self.chest_last_ts=None
            return False
        if (self.chest_candidate is None or self._overlap(box,self.chest_candidate)<.7 or
                (self.chest_last_ts is not None and now-self.chest_last_ts>3)):
            self.chest_candidate=box;self.chest_hits=1;self.chest_since=now
        else:
            self.chest_candidate=box;self.chest_hits+=1
        self.chest_last_ts=now
        return self.chest_hits>=2 and now-self.chest_since>=1.5

    def _appearance_search(self, gray, now):
        found=self.recovery.find(gray,self.previous)
        if found:
            self._confirm_recovery(gray,now,found['boxes'],found['confidence'],found['kind'])
            return True
        return False

    def _confirm_recovery(self, gray, now, boxes, score, kind):
        animal=boxes['animal']
        chest_verified=self._confirm_chest(boxes.get('respiration'),now)
        if self.candidate is None or self._overlap(animal,self.candidate)<.75:
            self.candidate=animal;self.candidate_hits=1;self.candidate_since=now
        else:
            self.candidate=animal;self.candidate_hits+=1
        self.reason='confirming_'+kind
        if self.candidate_hits<3 or now-self.candidate_since<2.0-1e-6:return
        if not chest_verified:
            boxes={'animal':animal}
        points=self._tracking_features(gray,boxes)
        if points is None or len(points)<12:return
        patch=self._patch(gray,animal)
        if not patch.size:return
        self.boxes=boxes;self.points=points;self.previous=gray.copy();self.last_ts=now
        self.feature_ts=now;self.confidence=float(score)
        self.template=self.cv.resize(patch,(64,64))
        self.anchor_patch=patch.copy();self.anchor_boxes=dict(boxes)
        self.respiration_ready='respiration' in boxes
        self.state='acquiring';self.reason='recovery_stabilizing';self.recovery_kind=kind
        self.stable_frames=0;self.recovery_since=now;self.motion_activity=0.0
        self.candidate=None;self.candidate_hits=0;self.candidate_since=None
        self.generation+=1

    @staticmethod
    def _overlap(a, b):
        x,y,w,h=a; xx,yy,ww,hh=b
        intersection=max(0,min(x+w,xx+ww)-max(x,xx))*max(0,min(y+h,yy+hh)-max(y,yy))
        return intersection/max(w*h+ww*hh-intersection,1)

    def _search(self, gray, now):
        # Search at most once per second, including when recovery is ambiguous.
        if self.search_ts is not None and now-self.search_ts < 1.0 - 1e-6:
            return
        if self.anchor_patch is None:
            # RTSP can start with incomplete/flat decoder frames. No reference
            # was established yet: retry the configured selection, bounded to 1 Hz.
            if 'animal' in self.initial_boxes:
                self.initialize(gray,self.initial_boxes,now)
                self.search_ts=now
            return
        if 'animal' not in self.anchor_boxes:
            return
        if self.search_ts is not None and now-self.search_ts > 2.5:
            self.candidate=None;self.candidate_hits=0;self.candidate_since=None
        self.search_ts=now
        # A persisted body-only rectangle may include enclosure background.
        # Revalidate appearance before accepting its rigid template at startup;
        # otherwise a strong background match can crop out the animal's head.
        if self.recovery_kind == 'cached' and self._appearance_search(gray, now):
            return
        cv,np=self.cv,self.np
        small=cv.resize(gray,None,fx=.5,fy=.5)
        candidates=[]
        for scale in (.9,1.0,1.1):
            h,w=self.anchor_patch.shape[:2]
            sw,sh=max(8,int(round(w*.5*scale))),max(8,int(round(h*.5*scale)))
            if sw>small.shape[1] or sh>small.shape[0]:continue
            template=cv.resize(self.anchor_patch,(sw,sh))
            scores=cv.matchTemplate(small,template,cv.TM_CCOEFF_NORMED)
            for _ in range(2):
                _,score,_,location=cv.minMaxLoc(scores)
                x,y=location
                if math.isfinite(score):candidates.append((score,(x*2,y*2,sw*2,sh*2)))
                scores[max(0,y-sh//2):min(scores.shape[0],y+sh//2+1),
                       max(0,x-sw//2):min(scores.shape[1],x+sw//2+1)]=-1
        candidates.sort(key=lambda item:item[0],reverse=True)
        distinct=[]
        for item in candidates:
            if all(self._overlap(item[1],old[1])<.35 for old in distinct):distinct.append(item)
        if (len(distinct)>1 and distinct[0][0]>=.90 and
                distinct[0][0]-distinct[1][0]<.08):
            self.candidate=None;self.candidate_hits=0;self.candidate_since=None
            self.reason='ambiguous_candidates'
            return
        if not distinct or distinct[0][0]<.90:
            if self._appearance_search(gray,now):return
            self.candidate=None;self.candidate_hits=0;self.candidate_since=None
            self.reason='searching_or_ambiguous'
            return
        score,animal=distinct[0]
        points=self._features(gray,animal)
        if points is None or len(points)<12:
            if self._appearance_search(gray,now):return
            self.candidate=None;self.candidate_hits=0;self.candidate_since=None
            return
        ax,ay,aw,ah=self.anchor_boxes['animal'];x,y,w,h=animal
        boxes={name:(x+(bx-ax)*w/aw,y+(by-ay)*h/ah,bw*w/aw,bh*h/ah)
               for name,(bx,by,bw,bh) in self.anchor_boxes.items()}
        # The chest must also resemble its original appearance, not just the body.
        if 'respiration' in boxes:
            original=self._patch(self.anchor_patch,(
                self.anchor_boxes['respiration'][0]-ax,self.anchor_boxes['respiration'][1]-ay,
                self.anchor_boxes['respiration'][2],self.anchor_boxes['respiration'][3]))
            current=self._patch(gray,boxes['respiration'])
            if (not original.size or not current.size or float(original.std())<8 or
                    float(current.std())<8):
                if self._appearance_search(gray,now):return
                self._confirm_recovery(gray,now,{'animal':animal},score,'template_body')
                return
            correlation=float(cv.matchTemplate(cv.resize(current,(32,32)),
                              cv.resize(original,(32,32)),cv.TM_CCOEFF_NORMED)[0,0])
            if not math.isfinite(correlation) or correlation<.85:
                if self._appearance_search(gray,now):return
                self._confirm_recovery(gray,now,{'animal':animal},score,'template_body')
                return
        self._confirm_recovery(gray,now,boxes,score,'template')

    def normalized_boxes(self, shape):
        height,width=shape[:2]
        return {name:{'x':x/width,'y':y/height,'width':w/width,'height':h/height}
                for name,(x,y,w,h) in self.boxes.items()}
