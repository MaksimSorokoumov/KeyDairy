from PIL import Image, ImageDraw, ImageFont

def create_icon(output_path='icon.ico'):
    # Базовое изображение (RGBA)
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    text = "KD"
    text_fill = (0, 255, 64, 255)

    # Пытаемся загрузить крупный шрифт, иначе используем дефолтный
    try:
        font = ImageFont.truetype("arial.ttf", 180)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 180)
        except Exception:
            font = ImageFont.load_default()

    # Вычисляем позицию текста по центру
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    pos = ((size - w) // 2, (size - h) // 2 - 8)

    draw.text(pos, text, font=font, fill=text_fill)

    # Сохраняем ICO с несколькими размерами
    sizes = [256, 128, 64, 48, 32, 16]
    try:
        img.save(output_path, format='ICO', sizes=[(s, s) for s in sizes])
        print(f"Иконка сохранена в {output_path}")
    except Exception as e:
        print(f"Не удалось сохранить иконку: {e}")

if __name__ == '__main__':
    create_icon()


