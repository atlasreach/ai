import zipfile
import os

# Path to the ZIP file (adjust if needed)
zip_path = 'hazel_training_dataset.zip'
extract_to = 'extracted_images'

# Extract the ZIP
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_to)

# Captions dictionary (for testing with 2 images)
captions = {
    '1.jpg': 'sarah, 1girl, solo, kneeling on floor with legs spread wide facing camera, right hand between legs left hand on breast, head tilted back eyes closed moaning, long curly black hair cascading down back, completely nude full frontal view pussy wet and visible, voluptuous figure huge breasts sagging slightly wide areolas erect nipples tiny waist flared hips olive skin belly button piercing, dim room light with shadows highlighting curves, low angle close-up, plain gray wall background, masterpiece, best quality, photorealistic, 8k',
    '2.jpg': 'sarah, 1girl, solo, lying on bed on back with legs raised and bent at knees, both hands gripping ankles spreading legs, head turned to side gazing seductively at camera, short bob red hair tousled, micro thong bikini top pushed up exposing breasts thong pulled aside labia spread, slim figure small perky breasts pink nipples flat stomach toned abs pale skin no marks, soft candlelight with warm glow, side view medium distance, bedroom with rumpled sheets and pillows, masterpiece, best quality, photorealistic, 8k'
}

# Process only .jpg files and create .txt with caption
for filename in os.listdir(extract_to):
    if filename.endswith('.jpg') and filename in captions:
        txt_filename = os.path.join(extract_to, filename.replace('.jpg', '.txt'))
        with open(txt_filename, 'w') as f:
            f.write(captions[filename])