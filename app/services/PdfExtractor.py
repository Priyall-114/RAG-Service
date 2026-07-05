import pdfplumber
import boto3
from app.config import settings
import tempfile
import re

def S3connect(s3_key:str):
    client=boto3.client( service_name="s3",
                                 aws_access_key_id=settings.aws_access_key,
                                 aws_secret_access_key=settings.aws_secret_key,
                                 region_name="ap-south-1")
    
    bucket=settings.aws_bucket_name
    tmp=tempfile.NamedTemporaryFile(delete=False ,suffix=".pdf")
    tmp_path=tmp.name
    tmp.close() #already given delete=false so file not gets deleteds
    client.download_file(bucket,s3_key,tmp_path)
    
    
    return tmp_path#local temp file path

def _clean_text(text: str) -> str:
    
    text = re.sub(r'\n{3,}', '\n\n', text)#removes 3 or more newlines
    text = re.sub(r' {2,}', ' ', text)#removes multiple in  between spaces
    return text.strip()



def extract_text(filePath:str)->str:
        full_content=""
        with pdfplumber.open(filePath) as pdf:#open method returns an instance of the pdfplumber.PDF class
            #pdfplumber keeps the pages separate. It does not mix all the text together automatically
            for page in pdf.pages:
                text=page.extract_text()
                if text:
                    full_content+=_clean_text(text)+"\n"
        return full_content.strip()

