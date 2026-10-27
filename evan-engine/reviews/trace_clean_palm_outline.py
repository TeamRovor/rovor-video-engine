from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image
cv2.setNumThreads(1);root=Path(__file__).resolve().parents[4];folder=root/'work/engine/evan-character/cartoon-v1';rows=[]
for side,name,wrist,elbow in [('left','body-rig/arm-left.png',[214,762],[275,625]),('right','open-palm-clean-v1/right-skin.png',[810,762],[749,625])]:
 p=folder/name;im=np.array(Image.open(p).convert('RGBA'));assert im.shape==(1536,1024,4);y,x=np.mgrid[:1536,:1024];axis=np.array(wrist)-elbow;axis=axis/np.linalg.norm(axis);s=(x-wrist[0])*axis[0]+(y-wrist[1])*axis[1];inside=(im[:,:,3]>127).astype('uint8');distance=cv2.distanceTransform(inside,cv2.DIST_L2,5);boundary=(inside>0)&(cv2.erode(inside,np.ones((3,3),np.uint8))==0)&(s>=45);band=(distance>0)&(distance<=6)&(s>=45);assert boundary.sum()>0
 metrics={}
 for threshold in [40,80,120]:
  ink=(im[:,:,:3].max(2)<threshold)&band;assert ink.any();metrics[str(threshold)]=dict(darkInkArea=int(ink.sum()),alphaBoundaryPixels=int(boundary.sum()),inkAreaPerBoundaryPixel=float(ink.sum()/boundary.sum()),darkInkDistance95=float(np.percentile(distance[ink],95)))
 rows.append(dict(side=side,source=name,sourceSha256=hashlib.sha256(p.read_bytes()).hexdigest(),metrics=metrics))
report=dict(method='Unposed native-body pixels; alpha>127, axial s>=45, inner6px silhouette band, RGB thresholds40/80/120. Proxy, not artist/anatomy approval.',sourceAlphaModified=False,rows=rows)
out=root/'outputs/evan-cartoon-clean-palm-continuous/Outline-Trace.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
