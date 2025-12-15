import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import PyPDF2
import requests
from bs4 import BeautifulSoup

# 1. Ayarları Yükle
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# API Anahtarı kontrolü
if not api_key:
    st.error("API Anahtarı bulunamadı! Lütfen .env dosyasını kontrol edin.")
    st.stop()

# Gemini Ayarları
genai.configure(api_key=api_key)
model = genai.GenerativeModel('models/gemini-flash-latest')

# Sayfa Yapılandırması
st.set_page_config(layout="centered", page_title="Ayasofya Chatbot")

# Başlık
st.title("ChatBot")

# --- YARDIMCI FONKSİYONLAR ---

def read_txt(file_path):
    """Basit metin dosyasını okur."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read() + "\n\n"
    except FileNotFoundError:
        return ""

def read_pdfs(folder_path):
    """Klasördeki tüm PDF dosyalarını okur."""
    text_content = ""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return ""
        
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            try:
                pdf_path = os.path.join(folder_path, filename)
                with open(pdf_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text_content += f"--- DOSYA: {filename} ---\n"
                    for page in pdf_reader.pages:
                        text_content += page.extract_text() + "\n"
                    text_content += "\n"
            except Exception as e:
                # Sessizce devam et
                pass
    return text_content

def read_websites(file_path):
    """Link dosyasındaki URL'leri ziyaret edip metinleri çeker."""
    text_content = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            urls = f.readlines()
            
        for url in urls:
            url = url.strip()
            if not url: continue
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Sadece paragrafları al
                    paragraphs = soup.find_all('p')
                    page_text = "\n".join([p.get_text() for p in paragraphs])
                    text_content += f"--- WEB SİTESİ: {url} ---\n{page_text}\n\n"
            except Exception as e:
                # Sessizce devam et
                pass
                
    except FileNotFoundError:
        return ""
    
    return text_content

# --- VERİLERİ YÜKLE ---
with st.spinner("Sistem Hazırlanıyor..."):
    # 1. TXT Dosyası
    txt_data = read_txt("ayasofya_bilgisi.txt")
    
    # 2. PDF Dosyaları
    pdf_data = read_pdfs("belgeler")
    
    # 3. Web Siteleri
    web_data = read_websites("linkler.txt")
    
    # Hepsini Birleştir
    full_context = f"{txt_data}\n{pdf_data}\n{web_data}"

# Eğer metin boşsa uyarı ver ama ekrana basma
if not full_context.strip():
    st.error("⚠️ Veri kaynağı boş!")
    st.stop()

# --- SADECE CHAT ARAYÜZÜ ---
# Geçmiş mesajları saklamak için session state kullanımı
if "messages" not in st.session_state:
    st.session_state.messages = []

# Geçmiş mesajları ekrana yazdır (Chat formatında)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Kullanıcıdan mesaj al
if prompt := st.chat_input("Ayasofya hakkında bir soru sorun..."):
    # 1. Kullanıcı mesajını ekrana yaz ve geçmişe ekle
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Prompt Mühendisliği
    system_instruction = f"""Sen yardımsever bir asistansın. Aşağıdaki 'KAYNAK METİN' içerisindeki bilgileri kullanarak kullanıcının sorusunu cevapla.
    
    Kurallar:
    1. Sadece verilen metindeki bilgileri kullan.
    2. Eğer sorunun cevabı metinde yoksa "Bu konuda kaynak metinde bilgi bulunmuyor." de.
    3. Asla ve asla metin dışından bilgi uydurma.
    
    KAYNAK METİN:
    {full_context}
    """
    
    full_prompt = f"{system_instruction}\n\nKullanıcı Sorusu: {prompt}"

    # 3. Gemini'den cevap al
    try:
        with st.spinner("Cevap hazırlanıyor..."):
            response = model.generate_content(full_prompt)
            answer = response.text
            
        # 4. Cevabı ekrana yaz ve geçmişe ekle
        st.chat_message("assistant").markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
