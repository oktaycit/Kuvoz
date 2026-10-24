"""Bounded scene/appearance detector for a fixed incubator camera."""
import os
import time


class AnimalDetector:
    def __init__(self, cv, np):
        self.cv, self.np = cv, np
        self.recovery = None
        self.last_ms = 0.0
        self.calls = 0
        self.hint = None
        self.template = None
        self.last_full = 0.0
        self.last_box = None
        self.last_hist = None
        self.last_seen = 0.0

    @property
    def available(self):
        return os.getenv('KUVOZ_AI_SCENE_TRACKING', '0') == '1'

    def attach(self, recovery, seed=None, box=None):
        self.recovery = recovery
        if recovery.scene_background is None and seed is not None:
            recovery.scene_background = seed.copy()
        if seed is not None and box is not None:
            recovery.observe_scene(seed)
            hist=self._histogram(seed,recovery.scene_mask,box)
            if hist is not None:
                self.last_box,self.last_hist,self.last_seen=tuple(box),hist,time.monotonic()

    def detect(self, frame):
        if self.recovery is None:
            return []
        start = time.monotonic()
        gray = self.cv.cvtColor(frame, self.cv.COLOR_BGR2GRAY)
        self.recovery.observe_scene(gray)
        found = None
        hint_score = 0.0
        if self.hint is not None and self.template is not None:
            patch=self.recovery._patch(gray,self.hint)
            foreground=self.recovery._patch(self.recovery.scene_mask,self.hint)
            if patch.size and foreground.size and self.cv.countNonZero(foreground)>foreground.size*.15:
                hint_score=float(self.cv.matchTemplate(self.cv.resize(patch,(64,64)),self.template,
                                                      self.cv.TM_CCOEFF_NORMED)[0,0])
                if hint_score>=.95 and start-self.last_full<60:
                    found={'boxes':{'animal':self.hint},'confidence':hint_score}
        if found is None:
            found = self.recovery.find(gray)
            self.last_full = start
            if found is None and hint_score>=.97 and self.hint is not None:
                found={'boxes':{'animal':self.hint},'confidence':hint_score}
            if found is None:
                found=self._continue_pose(gray,start)
            if found:
                # Periodic identity verification must not move a perfectly
                # stable surface ROI merely because the detector crop jitters.
                if (hint_score>=.95 and self.hint is not None and
                        self.recovery._iou(self.hint,found['boxes']['animal'])>=.5):
                    found={'boxes':{'animal':self.hint},'confidence':hint_score}
                patch=self.recovery._patch(gray,found['boxes']['animal'])
                if patch.size:self.template=self.cv.resize(patch,(64,64))
        self.last_ms = round((time.monotonic()-start)*1000, 1)
        self.calls += 1
        if not found:
            return []
        box = found['boxes']['animal']
        x,y,w,h = map(round,box)
        foreground = self.recovery.scene_mask[y:y+h,x:x+w]
        # A static enclosure feature must not become an animal. A verified old
        # torso can bootstrap a stationary animal before its bedding is seen.
        if ('respiration' not in found['boxes'] and
                (not foreground.size or self.cv.countNonZero(foreground)<foreground.size*.15)):
            return []
        hist=self._histogram(gray,self.recovery.scene_mask,box)
        if hist is not None:self.last_hist=hist
        self.last_box,self.last_seen=box,start
        return [{'box':box,'confidence':found['confidence']}]

    def _histogram(self, gray, mask, box):
        x,y,w,h=map(round,box)
        patch=gray[y:y+h,x:x+w];selected=mask[y:y+h,x:x+w]
        if not patch.size or self.cv.countNonZero(selected)<120:return None
        hist=self.cv.calcHist([patch],[0],selected,[32],[0,256]).ravel()+1
        return hist/hist.sum()

    def _continue_pose(self, gray, now):
        """Bridge a non-rigid pose change using recent spatial/scene evidence.

        This is bounded continuity of the already selected animal, not an
        unbounded histogram-only search for an unrelated new occupant.
        """
        if self.last_box is None or self.last_hist is None or now-self.last_seen>15:return None
        cv,np=self.cv,self.np
        mask=self.recovery.scene_mask.copy();height,width=gray.shape
        bx,by=max(2,round(width*.08)),max(2,round(height*.08))
        mask[:by]=0;mask[-by:]=0;mask[:,:bx]=0;mask[:,-bx:]=0
        for x,y,w,h in self.recovery.exclusions:
            padding=round(width*.02)
            mask[max(0,round(y*height)-padding):min(height,round((y+h)*height)+padding),
                 max(0,round(x*width)-padding):min(width,round((x+w)*width)+padding)]=0
        contours=cv.findContours(mask,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)[-2]
        px,py,pw,ph=self.last_box;area=pw*ph;candidates=[]
        for contour in contours:
            x,y,w,h=cv.boundingRect(contour)
            if not area*.25<=w*h<=min(area*2.5,gray.size*.4):continue
            if not .25<=w/max(h,1)<=4 or cv.contourArea(contour)<w*h*.3:continue
            if x<=bx or y<=by or x+w>=width-bx or y+h>=height-by:continue
            distance=((x+w/2-px-pw/2)**2+(y+h/2-py-ph/2)**2)**.5
            if distance>max(pw,ph)*1.5:continue
            hist=self._histogram(gray,mask,(x,y,w,h))
            if hist is None:continue
            likeness=float(np.minimum(hist,self.last_hist).sum())
            if likeness<(.75 if distance>max(pw,ph)*.65 else .65):continue
            candidates.append((likeness,(float(x),float(y),float(w),float(h))))
        candidates.sort(reverse=True)
        if not candidates:return None
        score,box=candidates[0]
        if any(self.recovery._iou(box,b)<.2 and other>=score-.1 for other,b in candidates[1:]):return None
        return {'boxes':{'animal':box},'confidence':min(.9,max(.82,score))}
