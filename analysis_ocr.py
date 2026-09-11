import base64,json,sys
import numpy as np
from PIL import Image
from io import BytesIO
from rapidocr_onnxruntime import RapidOCR
engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=2)
output=[]
for i,encoded in enumerate(json.load(sys.stdin)['images']):
    image=np.array(Image.open(BytesIO(base64.b64decode(encoded))).convert('RGB'))
    result,_=engine(image)
    output.append({'image':i+1,'lines':[{'text':line[1],'confidence':float(line[2])} for line in (result or [])]})
print(json.dumps(output))
