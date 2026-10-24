"""Atomic, bounded calibration checkpoint; no video history or pickled objects."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import BadZipFile


class ReferenceCache:
    def __init__(self, directory, identity, shape):
        self.signature=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        self.path=Path(directory)/'selected-camera.npz'
        self.shape=tuple(shape[:2])

    def _boxes(self, boxes):
        if not isinstance(boxes,dict) or 'animal' not in boxes:return None
        result={};height,width=self.shape
        for name,box in boxes.items():
            if name not in ('animal','respiration') or len(box)!=4:return None
            values=tuple(float(v) for v in box);x,y,w,h=values
            if not (0<=x<width and 0<=y<height and w>=1 and h>=1 and x+w<=width+.01 and y+h<=height+.01):
                return None
            result[name]=values
        return result

    def save(self, recovery, gray, boxes):
        np=recovery.np
        if not recovery.references or tuple(gray.shape)!=self.shape:return False
        meta={'version':1,'signature':self.signature,'shape':self.shape,'boxes':boxes,'references':[]}
        arrays={'frame':gray}
        if recovery.scene_background is not None:
            arrays['scene_background']=recovery.scene_background
        for i,ref in enumerate(recovery.references[:3]):
            meta['references'].append({'boxes':ref['boxes'],'chest':ref['chest'] is not None})
            for name in ('points','descriptors','hist','posterior'):
                arrays[str(i)+'_'+name]=ref[name]
            if ref['chest'] is not None:arrays[str(i)+'_chest']=ref['chest']
        arrays['metadata']=np.array(json.dumps(meta))
        temp=self.path.with_suffix('.tmp')
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with temp.open('wb') as stream:np.savez_compressed(stream,**arrays)
            os.replace(temp,self.path)
            return True
        except OSError:
            try:temp.unlink(missing_ok=True)
            except OSError:pass
            return False

    def migrate_from(self, recovery, previous_identity):
        """Re-key a fully validated checkpoint after the caller verifies camera identity.

        No permissive load fallback: future reads still require the new signature.
        Calibration, transform and resolution are part of both identities.
        """
        previous = ReferenceCache(self.path.parent, previous_identity, self.shape)
        restored = previous.load(recovery)
        if restored is None:
            return False
        frame, boxes = restored
        return self.save(recovery, frame, boxes)

    def load(self, recovery):
        np=recovery.np
        try:
            if self.path.stat().st_size>256000:return None
            with np.load(self.path,allow_pickle=False) as archive:
                if len(archive.files)>21:return None
                meta=json.loads(str(archive['metadata'].item()))
                if (meta.get('version')!=1 or meta.get('signature')!=self.signature or
                        tuple(meta.get('shape',[]))!=self.shape):return None
                frame=archive['frame']
                if frame.dtype!=np.uint8 or tuple(frame.shape)!=self.shape:return None
                boxes=self._boxes(meta['boxes'])
                if boxes is None or not 1<=len(meta['references'])<=3:return None
                references=[]
                for i,info in enumerate(meta['references']):
                    refboxes=self._boxes(info['boxes'])
                    points=archive[str(i)+'_points'];desc=archive[str(i)+'_descriptors']
                    hist=archive[str(i)+'_hist'];posterior=archive[str(i)+'_posterior']
                    if (refboxes is None or desc.dtype!=np.uint8 or desc.ndim!=2 or
                            not 8<=len(desc)<=240 or desc.shape[1]!=32 or
                            points.dtype!=np.float32 or points.shape!=(len(desc),2) or
                            not np.isfinite(points).all() or hist.shape!=(32,) or posterior.shape!=(32,) or
                            not np.isfinite(hist).all() or not np.isfinite(posterior).all() or
                            np.any(hist<0) or np.any(posterior<0) or np.any(posterior>1)):
                        return None
                    chest=archive[str(i)+'_chest'].copy() if info['chest'] else None
                    if chest is not None and (chest.dtype!=np.uint8 or chest.shape!=(32,32)):return None
                    references.append({'boxes':refboxes,'points':points.copy(),'descriptors':desc.copy(),
                        'hist':hist.astype(np.float32),'posterior':posterior.astype(np.float32),
                        'lookup':np.repeat((posterior>=.62).astype(np.uint8)*255,8),'chest':chest})
                background=archive['scene_background'].copy() if 'scene_background' in archive.files else None
                if background is not None and (background.dtype!=np.uint8 or tuple(background.shape)!=self.shape):return None
                result=(frame.copy(),boxes)
            recovery.references=references
            recovery.scene_background=background
            return result
        except (OSError,ValueError,KeyError,TypeError,BadZipFile,EOFError):
            return None
