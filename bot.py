import telebot
import os
import time
import threading
from datetime import datetime
from PIL import Image
from docx import Document
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
import csv

TOKEN = "8315427314:AAErsvSNx6THo5FwoAy8P4lZjpnQi_fETAU"
bot = telebot.TeleBot(TOKEN)

# ========== KANAL SOZLAMALARI ==========
CHANNEL_ID = "-1003705652043"  # Sizning kanal ID

# ========== GLOBAL O'ZGARUVCHILAR ==========
user_state = {}
user_page = {}
user_loading = {}

BASE = "files"
IN_DIR = f"{BASE}/in"
OUT_DIR = f"{BASE}/out"
os.makedirs(IN_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# ========== LOG FAYL ==========
LOG_FILE = "users_log.csv"

def init_log():
    """Log faylini yaratish"""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Vaqt', 'User ID', 'Username', 'Ism', 'Funksiya', 'Fayl nomi', 'Holat'])

def log_action(chat_id, username, first_name, function_name, filename, status="Success"):
    """Har bir amalni log qilish"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([now, chat_id, username or '-', first_name or '-', function_name, filename, status])

# ========== KANALGA XABAR JO'NATISH ==========
def send_to_channel(chat_id, username, first_name, function_name, filename, status="🔄"):
    """Foydalanuvchi harakatini kanalga jo'natadi"""
    try:
        now = datetime.now().strftime("%H:%M:%S")
        date = datetime.now().strftime("%d.%m.%Y")
        
        status_emoji = {
            "✅": "✅ MUVAFIQQIYATLI",
            "❌": "❌ XATOLIK",
            "🔄": "🔄 JARAYONDA",
            "⏳": "⏳ KUTILMOQDA"
        }.get(status, "📌")
        
        username_text = f"@{username}" if username else "Yo'q"
        
        message = f"""
<b>📢 YANGI HARAKAT</b> [{date}]

┌─ <b>👤 FOYDALANUVCHI</b>
├ ID: <code>{chat_id}</code>
├ Ism: <b>{first_name}</b>
├ Username: {username_text}
│
├─ <b>⚙️ AMAL</b>
├ Funksiya: <b>{function_name}</b>
├ Fayl: <code>{filename}</code>
│
└─ <b>🕐 VAQT</b> {now}

<b>{status_emoji}</b>
        """
        bot.send_message(CHANNEL_ID, message, parse_mode='HTML')
        return True
    except Exception as e:
        print(f"Kanalga jo'natishda xatolik: {e}")
        return False

def check_channel():
    """Kanalga xabar jo'natish huquqini tekshirish"""
    try:
        bot.send_message(CHANNEL_ID, "✅ Bot kanalga muvaffaqiyatli ulandi!")
        print("✅ Kanal ulanishi muvaffaqiyatli!")
        return True
    except Exception as e:
        print(f"❌ Kanalga ulanishda xatolik: {e}")
        print("👉 Botni kanalga ADMIN qilib qo'shing!")
        return False

# ========== KIRILL SHRIFTLARI ==========
try:
    pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
    FONT_NAME = 'DejaVu'
except:
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        FONT_NAME = 'DejaVu'
    except:
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            FONT_NAME = 'Arial'
        except:
            FONT_NAME = 'Helvetica'

# ========== LOADING ANIMATION ==========
def loading_animation(chat_id, message_id):
    frames = ["/", "-", "\\", "|"]
    texts = ["Qayta ishlanmoqda...", "Iltimos kuting...", "Fayl tayyorlanmoqda..."]
    i = 0
    while user_loading.get(chat_id, False):
        try:
            frame = frames[i % len(frames)]
            text = texts[i % len(texts)]
            bot.edit_message_text(f"{frame} {text}", chat_id, message_id)
            time.sleep(0.6)
            i += 1
        except:
            pass

def start_loading(chat_id, text="Qayta ishlanmoqda..."):
    msg = bot.send_message(chat_id, text)
    user_loading[chat_id] = True
    threading.Thread(target=loading_animation, args=(chat_id, msg.message_id), daemon=True)
    return msg

def stop_loading(chat_id):
    user_loading[chat_id] = False
    time.sleep(0.6)

# ========== ASOSIY FUNKSIYALAR ==========
def word_to_pdf(input_path, output_path):
    doc = Document(input_path)
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setFont(FONT_NAME, 11)
    width, height = A4
    y = height - 50
    left_margin = 60
    right_margin = width - 60
    line_height = 14
    
    for paragraph in doc.paragraphs:
        text = paragraph.text
        if not text:
            y -= line_height
            continue
        words = text.split()
        line = ""
        for word in words:
            test_line = line + " " + word if line else word
            if c.stringWidth(test_line, FONT_NAME, 11) < (right_margin - left_margin):
                line = test_line
            else:
                if y < 50:
                    c.showPage()
                    c.setFont(FONT_NAME, 11)
                    y = height - 50
                try:
                    c.drawString(left_margin, y, line)
                except:
                    c.drawString(left_margin, y, line.encode('latin-1', 'ignore').decode('latin-1'))
                y -= line_height
                line = word
        if line:
            if y < 50:
                c.showPage()
                c.setFont(FONT_NAME, 11)
                y = height - 50
            try:
                c.drawString(left_margin, y, line)
            except:
                c.drawString(left_margin, y, line.encode('latin-1', 'ignore').decode('latin-1'))
            y -= line_height
        y -= 5
    c.save()
    return True

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def pdf_to_word(pdf_path, output_path):
    text = extract_text_from_pdf(pdf_path)
    doc = Document()
    for para in text.split('\n'):
        if para.strip():
            doc.add_paragraph(para.strip())
    doc.save(output_path)
    return True

def pdf_to_excel(pdf_path, output_path):
    text = extract_text_from_pdf(pdf_path)
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "PDF Data"
    for i, line in enumerate(text.split('\n'), 1):
        if line.strip():
            sheet.cell(row=i, column=1, value=line.strip())
    wb.save(output_path)
    return True

def image_to_pdf(input_path, output_path):
    img = Image.open(input_path).convert("RGB")
    img.save(output_path, "PDF")
    return True

def excel_to_pdf(input_path, output_path):
    if input_path.lower().endswith('.csv'):
        rows = []
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            for row in csv.reader(f):
                rows.append(row)
    else:
        wb = openpyxl.load_workbook(input_path, data_only=True)
        sheet = wb.active
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([str(cell) if cell else "" for cell in row])
    
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setFont(FONT_NAME, 10)
    width, height = A4
    y = height - 50
    left_margin = 50
    row_height = 14
    for row in rows:
        line = " | ".join(row)
        if len(line) > 120:
            line = line[:117] + "..."
        if y < 50:
            c.showPage()
            c.setFont(FONT_NAME, 10)
            y = height - 50
        try:
            c.drawString(left_margin, y, line)
        except:
            c.drawString(left_margin, y, line.encode('latin-1', 'ignore').decode('latin-1'))
        y -= row_height
    c.save()
    return True

def pdf_to_jpg(pdf_path, output_dir):
    import fitz
    doc = fitz.open(pdf_path)
    output_paths = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        output_path = os.path.join(output_dir, f"page_{i+1}.jpg")
        pix.save(output_path)
        output_paths.append(output_path)
    doc.close()
    return output_paths

def remove_pages(input_path, pages_to_remove, output_path):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    if isinstance(pages_to_remove, int):
        pages_to_remove = [pages_to_remove]
    for i, page in enumerate(reader.pages):
        if (i + 1) not in pages_to_remove:
            writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return True

# ========== MENU ==========
def menu():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("JPG TO PDF", "WORD TO PDF", "EXCEL TO PDF", "PDF TO JPG", "PDF TO WORD", "PDF TO EXCEL", "REMOVE PAGES")
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    send_to_channel(m.chat.id, m.from_user.username, m.from_user.first_name, "👋 START", "-", "🔄")
    log_action(m.chat.id, m.from_user.username, m.from_user.first_name, "START", "-", "Success")
    
    bot.send_message(m.chat.id, 
        f"Xush kelibsiz {m.from_user.first_name}!\n\n"
        "SALOM, USHBU BOT TEST REJIMIDA ISHLAYAPTI\n"
        "AGAR BOTDA MUOMMO KUZATILSA @sardorbek_abdullaev TEL:990043637 BILAN BOG'LANING!\n\n"
        "Mavjud funksiyalar:\n"
        "------------------------\n"
        "JPG TO PDF - Rasmdan PDF\n"
        "WORD TO PDF - Worddan PDF (doc, docx)\n"
        "EXCEL TO PDF - Exceldan PDF (xls, xlsx, csv)\n"
        "PDF TO JPG - PDF dan rasm\n"
        "PDF TO WORD - PDF dan Word\n"
        "PDF TO EXCEL - PDF dan Excel\n"
        "REMOVE PAGES - Sahifa ochirish\n"
        "------------------------\n\n"
        "Quyidagi menyudan birini tanlang:",
        reply_markup=menu())

@bot.message_handler(commands=['get_id'])
def get_id(m):
    bot.reply_to(m, f"Bu chat ID: `{m.chat.id}`", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in ["JPG TO PDF", "WORD TO PDF", "EXCEL TO PDF", "PDF TO JPG", "PDF TO WORD", "PDF TO EXCEL", "REMOVE PAGES"])
def select(m):
    user_state[m.chat.id] = m.text
    bot.send_message(m.chat.id, "Faylni yuboring")
    send_to_channel(m.chat.id, m.from_user.username, m.from_user.first_name, f"📌 {m.text} tanlandi", "-", "🔄")

# ========== ASOSIY HANDLER ==========
@bot.message_handler(content_types=['document', 'photo'])
def file_handler(m):
    chat_id = m.chat.id
    if chat_id not in user_state:
        bot.send_message(chat_id, "Avval menyudan funksiyani tanlang!", reply_markup=menu())
        return
    
    func = user_state[chat_id]
    start_loading(chat_id, "Yuklanmoqda...")
    
    try:
        if m.document:
            file_info = bot.get_file(m.document.file_id)
            original_name = m.document.file_name
        else:
            file_info = bot.get_file(m.photo[-1].file_id)
            original_name = "image.jpg"
        
        data = bot.download_file(file_info.file_path)
        in_path = f"{IN_DIR}/{int(time.time())}_{original_name}"
        with open(in_path, "wb") as f:
            f.write(data)
        
        base_name = os.path.splitext(original_name)[0]
        
        # Kanalga va logga yozish
        send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "⏳ Jarayon boshlandi")
        log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Started")
        
        # REMOVE PAGES
        if func == "REMOVE PAGES":
            if not original_name.lower().endswith('.pdf'):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat PDF fayl yuboring!")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: PDF emas")
                return
            stop_loading(chat_id)
            user_page[chat_id] = in_path
            bot.send_message(chat_id, "Qaysi sahifani ochirish kerak?\nMasalan: 3 yoki 1,3,5")
            return
        
        # JPG TO PDF
        elif func == "JPG TO PDF":
            if not original_name.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat rasm fayli yuboring!")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: Rasm emas")
                return
            out_path = f"{OUT_DIR}/{base_name}.pdf"
            stop_loading(chat_id)
            start_loading(chat_id, "JPG -> PDF...")
            image_to_pdf(in_path, out_path)
            stop_loading(chat_id)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f)
            send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "✅ Muvaffaqiyatli")
            log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Success")
            os.remove(in_path)
            os.remove(out_path)
            del user_state[chat_id]
            return
        
        # WORD TO PDF
        elif func == "WORD TO PDF":
            if not (original_name.lower().endswith('.doc') or original_name.lower().endswith('.docx')):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat Word fayli yuboring! (doc, docx)")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: Word emas")
                return
            out_path = f"{OUT_DIR}/{base_name}.pdf"
            stop_loading(chat_id)
            start_loading(chat_id, "WORD -> PDF...")
            word_to_pdf(in_path, out_path)
            stop_loading(chat_id)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f)
            send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "✅ Muvaffaqiyatli")
            log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Success")
            os.remove(in_path)
            os.remove(out_path)
            del user_state[chat_id]
            return
        
        # EXCEL TO PDF
        elif func == "EXCEL TO PDF":
            if not (original_name.lower().endswith('.xls') or original_name.lower().endswith('.xlsx') or original_name.lower().endswith('.csv')):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat Excel fayli yuboring! (xls, xlsx, csv)")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: Excel emas")
                return
            out_path = f"{OUT_DIR}/{base_name}.pdf"
            stop_loading(chat_id)
            start_loading(chat_id, "EXCEL -> PDF...")
            excel_to_pdf(in_path, out_path)
            stop_loading(chat_id)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f)
            send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "✅ Muvaffaqiyatli")
            log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Success")
            os.remove(in_path)
            os.remove(out_path)
            del user_state[chat_id]
            return
        
        # PDF TO WORD
        elif func == "PDF TO WORD":
            if not original_name.lower().endswith('.pdf'):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat PDF fayl yuboring!")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: PDF emas")
                return
            out_path = f"{OUT_DIR}/{base_name}.docx"
            stop_loading(chat_id)
            start_loading(chat_id, "PDF -> WORD...")
            pdf_to_word(in_path, out_path)
            stop_loading(chat_id)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f)
            send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "✅ Muvaffaqiyatli")
            log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Success")
            os.remove(in_path)
            os.remove(out_path)
            del user_state[chat_id]
            return
        
        # PDF TO EXCEL
        elif func == "PDF TO EXCEL":
            if not original_name.lower().endswith('.pdf'):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat PDF fayl yuboring!")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: PDF emas")
                return
            out_path = f"{OUT_DIR}/{base_name}.xlsx"
            stop_loading(chat_id)
            start_loading(chat_id, "PDF -> EXCEL...")
            pdf_to_excel(in_path, out_path)
            stop_loading(chat_id)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f)
            send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "✅ Muvaffaqiyatli")
            log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Success")
            os.remove(in_path)
            os.remove(out_path)
            del user_state[chat_id]
            return
        
        # PDF TO JPG
        elif func == "PDF TO JPG":
            if not original_name.lower().endswith('.pdf'):
                stop_loading(chat_id)
                bot.send_message(chat_id, "Faqat PDF fayl yuboring!")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "❌ Xato: PDF emas")
                return
            stop_loading(chat_id)
            start_loading(chat_id, "PDF -> JPG...")
            try:
                output_paths = pdf_to_jpg(in_path, OUT_DIR)
                if not output_paths:
                    stop_loading(chat_id)
                    bot.send_message(chat_id, "Sahifalar topilmadi!")
                    return
                stop_loading(chat_id)
                bot.send_message(chat_id, f"{len(output_paths)} ta sahifa topildi")
                for img_path in output_paths:
                    with open(img_path, "rb") as f:
                        bot.send_photo(chat_id, f)
                    os.remove(img_path)
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, f"✅ {len(output_paths)} ta rasm yaratildi")
                log_action(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, "Success")
                os.remove(in_path)
                del user_state[chat_id]
            except Exception as e:
                stop_loading(chat_id)
                bot.send_message(chat_id, f"Xatolik: {str(e)[:100]}\nPyMuPDF o'rnating: pip install PyMuPDF")
                send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, func, original_name, f"❌ Xato: {str(e)[:50]}")
            return
    
    except Exception as e:
        stop_loading(chat_id)
        error_msg = f"Xatolik: {str(e)[:100]}"
        bot.send_message(chat_id, error_msg)
        send_to_channel(chat_id, m.from_user.username, m.from_user.first_name, user_state.get(chat_id, "Unknown"), original_name if 'original_name' in dir() else "-", f"❌ {str(e)[:50]}")
        log_action(chat_id, m.from_user.username, m.from_user.first_name, user_state.get(chat_id, "Unknown"), original_name if 'original_name' in dir() else "-", f"Error: {str(e)[:50]}")
        if chat_id in user_state:
            del user_state[chat_id]

# ========== SAHIFA O'CHIRISH ==========
@bot.message_handler(func=lambda m: m.chat.id in user_page)
def handle_page_number(m):
    chat_id = m.chat.id
    in_path = user_page[chat_id]
    start_loading(chat_id, "Sahifalar ochirilmoqda...")
    
    try:
        text = m.text.strip()
        if ',' in text:
            pages = [int(p.strip()) for p in text.split(',')]
        else:
            pages = [int(text)]
        
        original_name = os.path.basename(in_path)
        original_name = original_name.split('_', 1)[-1]
        base_name = os.path.splitext(original_name)[0]
        out_path = f"{OUT_DIR}/{base_name}_edited.pdf"
        
        remove_pages(in_path, pages, out_path)
        stop_loading(chat_id)
        
        with open(out_path, "rb") as f:
            bot.send_document(chat_id, f)
        
        # Kanalga va logga yozish
        user = bot.get_chat(chat_id)
        send_to_channel(chat_id, user.username, user.first_name, "✂️ REMOVE PAGES", f"{original_name} | Sahifalar: {pages}", "✅ Muvaffaqiyatli")
        log_action(chat_id, user.username, user.first_name, "REMOVE PAGES", f"{original_name}", f"Removed pages: {pages}")
        
        del user_page[chat_id]
        del user_state[chat_id]
        os.remove(in_path)
        os.remove(out_path)
        
    except ValueError:
        stop_loading(chat_id)
        bot.send_message(chat_id, "Notogri format!\nFaqat raqam yuboring.\nMasalan: 3 yoki 1,3,5")
    except Exception as e:
        stop_loading(chat_id)
        bot.send_message(chat_id, f"Xatolik: {str(e)[:100]}")

# ========== TOZALASH ==========
def cleanup_old_files():
    while True:
        time.sleep(3600)
        for folder in [IN_DIR, OUT_DIR]:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if time.time() - os.path.getctime(file_path) > 7200:
                    try:
                        os.remove(file_path)
                    except:
                        pass

threading.Thread(target=cleanup_old_files, daemon=True).start()

# ========== BOTNI ISHGA TUSHIRISH ==========
if __name__ == "__main__":
    print("🚀 Bot ishga tushmoqda...")
    init_log()
    check_channel()
    print("🤖 Bot ishlayapti...")
    print("📊 Kanal ID: -1003705652043")
    print("📝 Log fayl: users_log.csv")
    bot.infinity_polling()
