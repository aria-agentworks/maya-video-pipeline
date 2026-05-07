import replicate
import boto3
import botocore
import requests
import os
import sys

# --- Configuration ---
# Replicate API key from environment variable
REPLICATE_API_KEY = os.environ.get("REPLICATE_API_TOKEN", "")
if not REPLICATE_API_KEY:
    print("ERROR: REPLICATE_API_TOKEN environment variable not set!")
    sys.exit(1)
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY

# R2 Configuration
R2_ACCOUNT_ID = "a970eb068f3a6e1001defd42696cd440"
R2_BUCKET = "qte2wq7f5yx91i2k4uoye3u8pln544fp"
R2_ENDPOINT = "https://a970eb068f3a6e1001defd42696cd440.r2.cloudflarestorage.com"
R2_ACCESS_KEY = "afd7dba583ae4a2225f5c0feede764ada51d69dddad1dc8507d3e3c578dc4ef7"
R2_SECRET_KEY = "afd7dba583ae4a2225f5c0feede764ada51d69dddad1dc8507d3e3c578dc4ef7"
R2_PUBLIC_DOMAIN = "https://pub-85573262a9e846c5896860df66eb8299.r2.dev"

# Google Drive reference image URLs
REF_IMAGE_URL_1 = "https://drive.google.com/uc?id=1R1-PNzHJDkL5gaVqDzr-rr7XX2X9wdp1&export=download"
REF_IMAGE_URL_2 = "https://drive.google.com/uc?id=1xHSSA-3--NoqbY76BTWcZUFW9WM_BhWy&export=download"

MODEL_VERSION = "bytedance/flux-pulid:8baa7ef2255075b46f4d91cd238c21d31181b3e6a864463f967960bb0112525b"

# Prompts
PROMPT_1 = "Maya wearing a casual white top, sitting in a coffee shop with warm morning light, looking at camera with a relaxed smile, photorealistic, professional photography"
PROMPT_2 = "Maya in a stylish black outfit, on a city rooftop at sunset, candid pose looking over the city, golden hour lighting, photorealistic, professional photography"

def upload_to_r2(file_path, r2_key):
    print(f"Uploading {file_path} to R2 at {r2_key}...")
    s3_client = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=botocore.config.Config(s3={"addressing_style": "virtual"}),
        region_name="auto",
    )
    with open(file_path, "rb") as f:
        s3_client.upload_fileobj(f, R2_BUCKET, r2_key)
    public_url = f"{R2_PUBLIC_DOMAIN}/{r2_key}"
    print(f"Uploaded! Public URL: {public_url}")
    return public_url

def download_reference_image(url, local_path):
    print(f"Downloading reference image from {url}...")
    response = requests.get(url, allow_redirects=True, timeout=60)
    response.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(response.content)
    print(f"Downloaded to {local_path} ({len(response.content)} bytes)")
    return local_path

def generate_image(prompt, ref_image_url, output_path):
    print(f"Generating image for prompt: {prompt[:50]}...")
    print(f"Using reference image: {ref_image_url}")
    output = replicate.run(
        MODEL_VERSION,
        input={
            "prompt": prompt,
            "main_face_image": ref_image_url,
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
    print(f"Replicate output: {output}")
    if output and len(output) > 0:
        image_url = output[0]
        print(f"Downloading generated image from {image_url}...")
        img_response = requests.get(image_url, timeout=120)
        img_response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(img_response.content)
        print(f"Saved generated image to {output_path} ({len(img_response.content)} bytes)")
        return True
    else:
        print(f"ERROR: No output from Replicate!")
        return False

def main():
    print("=" * 60)
    print("Maya Test Image Generator")
    print("=" * 60)
    ref_local_1 = "/tmp/maya_ref_1.jpg"
    ref_local_2 = "/tmp/maya_ref_2.jpg"
    try:
        download_reference_image(REF_IMAGE_URL_1, ref_local_1)
    except Exception as e:
        print(f"ERROR downloading reference image 1: {e}")
        sys.exit(1)
    try:
        download_reference_image(REF_IMAGE_URL_2, ref_local_2)
    except Exception as e:
        print(f"ERROR downloading reference image 2: {e}")
        sys.exit(1)
    try:
        ref_r2_url_1 = upload_to_r2(ref_local_1, "ref/maya_ref_1.jpg")
        ref_r2_url_2 = upload_to_r2(ref_local_2, "ref/maya_ref_2.jpg")
    except Exception as e:
        print(f"ERROR uploading reference images to R2: {e}")
        sys.exit(1)
    local_output_1 = "/tmp/maya_coffee_shop.png"
    try:
        success = generate_image(PROMPT_1, ref_r2_url_1, local_output_1)
        if not success:
            print("ERROR: Failed to generate image 1")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR generating image 1: {e}")
        sys.exit(1)
    try:
        final_url_1 = upload_to_r2(local_output_1, "test/maya_coffee_shop.png")
        print(f"FINAL URL 1: {final_url_1}")
    except Exception as e:
        print(f"ERROR uploading image 1 to R2: {e}")
        sys.exit(1)
    local_output_2 = "/tmp/maya_rooftop.png"
    try:
        success = generate_image(PROMPT_2, ref_r2_url_2, local_output_2)
        if not success:
            print("ERROR: Failed to generate image 2")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR generating image 2: {e}")
        sys.exit(1)
    try:
        final_url_2 = upload_to_r2(local_output_2, "test/maya_rooftop.png")
        print(f"FINAL URL 2: {final_url_2}")
    except Exception as e:
        print(f"ERROR uploading image 2 to R2: {e}")
        sys.exit(1)
    print("=" * 60)
    print("SUCCESS! Both images generated and uploaded.")
    print(f"Coffee Shop: {final_url_1}")
    print(f"Rooftop: {final_url_2}")
    print("=" * 60)

if __name__ == "__main__":
    main()
