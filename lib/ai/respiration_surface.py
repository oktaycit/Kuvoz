"""Conservative periodic-motion check for an automatically selected body surface.

Stores only four scalar channels; never treats a silhouette as a respiration rate.
"""
from collections import deque
import math


class RespirationSurface:
    def __init__(self, cv, np):
        self.cv, self.np = cv, np
        self.samples = deque(maxlen=400)
        self.background_reference = None

    def reset(self):
        self.samples.clear()
        self.background_reference = None

    def add(self, frame, box, body, now):
        cv,np=self.cv,self.np
        gray=cv.cvtColor(frame,cv.COLOR_BGR2GRAY)
        x,y,w,h=map(round,box);patch=gray[y:y+h,x:x+w]
        if patch.size<120:return
        bx,by,bw,bh=map(round,body)
        # Robust global illumination reference outside the animal.
        sample=gray[::4,::4].astype(np.float32)
        mask=np.ones_like(sample,dtype=bool)
        mask[max(0,by//4):min(mask.shape[0],(by+bh+3)//4),max(0,bx//4):min(mask.shape[1],(bx+bw+3)//4)]=False
        if self.background_reference is None:
            self.background_reference=sample.copy()
        reference=self.background_reference
        valid=mask & (reference>10)&(reference<235)&(sample>10)&(sample<235)
        gain,offset=1.,0.
        for _ in range(2):
            a,b=reference[valid],sample[valid]
            if len(a)<50 or float(a.std())<10:return
            centered=a-a.mean()
            gain=float(np.mean(centered*(b-b.mean()))/np.mean(centered**2))
            offset=float(b.mean()-gain*a.mean())
            valid &= np.abs(sample-(gain*reference+offset))<8
        if not .5<gain<2:return
        if float(np.mean(np.abs(sample[valid]-(gain*reference[valid]+offset))))>3:return
        half=patch.shape[0]//2;mid=patch.shape[1]//2
        parts=[patch[:half,:mid],patch[:half,mid:],patch[half:,:mid],patch[half:,mid:]]
        self.samples.append((float(now),[(float(p.mean())-offset)/gain for p in parts]))
        while self.samples and now-self.samples[0][0]>60:self.samples.popleft()

    def estimate(self):
        np=self.np
        base={'status':'NOT_ENOUGH_DATA','reason':'searching_periodic_motion','respiration_bpm':None,'confidence':0.,
              'method':'surface_motion_autocorrelation'}
        if len(self.samples)<90:return base
        times=np.array([s[0] for s in self.samples]);duration=float(times[-1]-times[0])
        if duration<30 or (len(times)-1)/duration<3 or float(np.max(np.diff(times)))>1:return base
        grid=np.arange(times[0],times[-1],.2)
        values=np.array([s[1] for s in self.samples]);channels=[];peaks=[];supports=[]
        frequencies=np.fft.rfftfreq(len(grid),.2);band=(frequencies>=5/60)&(frequencies<=80/60)
        for column in values.T:
            signal=np.interp(grid,times,column)
            # Remove an affine trend before testing independent surface patches.
            trend=np.polyval(np.polyfit(np.arange(len(signal)),signal,1),np.arange(len(signal)))
            signal=signal-trend
            if float(np.std(signal))<.08:
                peaks.append(None);supports.append(0.);channels.append(signal);continue
            power=np.abs(np.fft.rfft(signal*np.hanning(len(signal))))**2
            filtered=np.where(band,power,0.);index=int(np.argmax(filtered));frequency=float(frequencies[index])
            support=float(power[max(1,index-1):index+2].sum()/max(float(power[band].sum()),1e-9))
            peaks.append(frequency if support>=.65 else None);supports.append(support);channels.append(signal)
        valid=[p for p in peaks if p is not None]
        if len(valid)<3:return base
        frequency=float(np.median(valid))
        agreeing=[i for i,p in enumerate(peaks) if p is not None and abs(p-frequency)<=max(.035,frequency*.1)]
        if len(agreeing)<3 or duration*frequency<5:return base
        # A common periodic component must have repeatable cycles, not just one
        # isolated FFT peak caused by a posture change or a brightness ramp.
        combined=np.mean([channels[i]/max(float(np.std(channels[i])),1e-9) for i in agreeing],axis=0)
        lag=round(5/frequency)
        if not 3<=lag<len(combined)//2:return base
        a,b=combined[:-lag],combined[lag:]
        corr=float(np.corrcoef(a,b)[0,1]) if np.std(a)>1e-6 and np.std(b)>1e-6 else 0.
        if not math.isfinite(corr) or corr<.7:return base
        confidence=min(.95,.5+.3*corr+.15*min(supports[i] for i in agreeing))
        return {'status':'OK','respiration_bpm':round(frequency*60,1),'confidence':round(confidence,2),
                'method':'surface_motion_autocorrelation','window_seconds':round(duration,1)}
