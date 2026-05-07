import replicate
import requests
import os
import json
import time
from urllib.parse import urlparse

REPLICATE_API_TOKEN = "3DMpso4TTvWbJKs5xm7PxyozQgk"

# R2 Config
R2_ACCOUNT_ID = "a970eb068f3a6e1001defd42696cd440"
R2_BUCKET = "qte2wq7f5yx91i2k4uoye3u8pln544fp"
R2_ENDPOINT = "https://a970eb068f3a6e1001defd42696cd440.r2.cloudflarestorage.com"
R2_ACCESS_KEY = "afd7dba583ae4a2225f5c0feede764ada51d69dddad1dc8507d3e3c578dc4ef7"
R2_SECRET_KEY = "afd7dba583ae4a2225f5c0feede764ada51d69dddad1dc8507d3e3c578dc4ef7"
R2_PUBLIC_DOMAIN = "https://pub-85573262a9e846c5896860df66eb8299.r2.dev"

# Reference images (Google Drive direct download URLs)
REF_IMAGE_1 = "https://drive.google.com/uc?id=1R1-PNzHJDkL5gaVqDzr-rr7XX2X9wdp1&export=download"
REF_IMAGE_2 = "https://drive.google.com/uc?id=1xHSSA-3--NoqbY76BTWcZUFW9WM_BhWy&export=download"

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


def upload_to_r2(file_path, object_key):
    """Upload a file to Cloudflare R2 using S3-compatible API"""
    import boto3
    from botocore.config import Config
    
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    
    with open(file_path, "rb") as f:
        client.put_object(Bucket=R2_BUCKET, Key=object_key, Body=f, ContentType="image/png")
    
    return f"{R2_PUBLIC_DOMAIN}/{object_key}"


def generate_image(prompt, ref_image_url, output_filename):
    """Generate an image using Replicate flux-pulid with face consistency"""
    print(f"Generating: {prompt[:60]}...")
    
    model_version = "bytedance/flux-pulid"
    
    output = replicate.run(
        model_version,
        input={
            "main_face_image": ref_image_url,
            "prompt": prompt,
            "width": 896,
            "height": 1152,
            "num_steps": 20,
            "start_step": 4,
            "guidance_scale": 4,
            "id_weight": 1.5,
            "num_outputs": 1,
            "true_cfg": 1.0,
            "output_format": "png",
            "output_quality": 95,
        }
    )
    
    print(f"Output received: {output}")
    
    # The output is a list of URLs
    if isinstance(output, list) and len(output) > 0:
        image_url = output[0]
    elif isinstance(output, str):
        image_url = output
    else:
        print(f"Unexpected output format: {output}")
        return None
    
    # Download the image
    print(f"Downloading from: {image_url}")
    resp = requests.get(image_url, timeout=300)
    resp.raise_for_status()
    
    with open(output_filename, "wb") as f:
        f.write(resp.content)
    
    return output_filename

# Generate Test Image 1
print("=" * 60)
print("GENERATING TEST IMAGE 1: Maya in Coffee Shop")
print("=" * 60)
local_file_1 = generate_image(
    "A young south asian woman with a warm relaxed smile, wearing a casual white top, sitting in a coffee shop with warm morning light streaming through windows, looking at camera, photorealistic, cinematic, soft natural lighting",
    REF_IMAGE_1,
    "maya_coffee_shop.png"
)

# Generate Test Image 2
print("=" * 60)
print("GENERATING TEST IMAGE 2: Maya on Rooftop")
print("=" * 60)
local_file_2 = generate_image(
    "A young south asian woman in a stylish black outfit, standing on a city rooftop at golden hour sunset, candid pose looking over the city skyline, warm golden light, photorealistic, cinematic, bokeh background",
    REF_IMAGE_2,
    "maya_rooftop.png"
)

# Upload to R2
print("=" * 60)
print("UPLOADING TO R2")
print("=" * 60)

if local_file_1:
    public_url_1 = upload_to_r2(local_file_1, "test/maya_coffee_shop.png")
    print(f"Image 1 uploaded: {public_url_1}")

if local_file_2:
    public_url_2 = upload_to_r2(local_file_2, "test/maya_rooftop.png")
    print(f"Image 2 uploaded: {public_url_2}")

# Output results as JSON for the workflow to capture
results = {}
if local_file_1:
    results["image_1"] = f"{R2_PUBLIC_DOMAIN}/test/maya_coffee_shop.png"
if local_file_2:
    results["image_2"] = f"{R2_PUBLIC_DOMAIN}/test/maya_rooftop.png"

print("=" * 60)
print("RESULTS JSON:")
print(json.dumps(results, indent=2))
