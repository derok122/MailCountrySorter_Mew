from PIL import Image, ImageDraw, ImageFont

def make_icon(path='app.ico'):
    size = 256
    img = Image.new('RGBA', (size, size), (6, 86, 179, 255))
    draw = ImageDraw.Draw(img)
    # draw a white rounded rectangle
    margin = 28
    draw.rectangle([margin, margin, size - margin, size - margin], fill=(255,255,255,255))
    # optional letter
    try:
        f = ImageFont.load_default()
        draw.text((size//2-16, size//2-10), 'M', font=f, fill=(6,86,179,255))
    except Exception:
        pass
    img.save(path, format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])

if __name__ == '__main__':
    make_icon()
