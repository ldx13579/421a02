import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import current_app

def generate_captcha(length=None):
    if length is None:
        length = current_app.config.get('CAPTCHA_LENGTH', 4)
    
    characters = string.ascii_uppercase + string.digits
    captcha_text = ''.join(random.choice(characters) for _ in range(length))
    return captcha_text

def create_captcha_image(captcha_text, width=None, height=None):
    if width is None:
        width = current_app.config.get('CAPTCHA_WIDTH', 120)
    if height is None:
        height = current_app.config.get('CAPTCHA_HEIGHT', 40)
    
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except IOError:
            font = ImageFont.load_default()
    
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))
    
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point([x, y], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    bbox = draw.textbbox((0, 0), captcha_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    for i, char in enumerate(captcha_text):
        char_x = x + i * (text_width // len(captcha_text))
        char_y = y + random.randint(-5, 5)
        color = (random.randint(0, 120), random.randint(0, 120), random.randint(0, 120))
        draw.text((char_x, char_y), char, font=font, fill=color)
    
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer
