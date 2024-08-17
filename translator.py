import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import os
import shutil
import ebooklib
import platform
import subprocess
from ebooklib import epub
from bs4 import BeautifulSoup as bs
from googletrans import Translator

# List of languages
LANGUAGES = {'af': 'afrikaans', 'sq': 'albanian', 'am': 'amharic', 'ar': 'arabic', 'hy': 'armenian', 'az': 'azerbaijani', 'eu': 'basque', 'be': 'belarusian', 'bn': 'bengali', 'bs': 'bosnian', 'bg': 'bulgarian', 'ca': 'catalan', 'ceb': 'cebuano', 'ny': 'chichewa', 'zh-cn': 'chinese (simplified)', 'zh-tw': 'chinese (traditional)', 'co': 'corsican', 'hr': 'croatian', 'cs': 'czech', 'da': 'danish', 'nl': 'dutch', 'en': 'english', 'eo': 'esperanto', 'et': 'estonian', 'tl': 'filipino', 'fi': 'finnish', 'fr': 'french', 'fy': 'frisian', 'gl': 'galician', 'ka': 'georgian', 'de': 'german', 'el': 'greek', 'gu': 'gujarati', 'ht': 'haitian creole', 'ha': 'hausa', 'haw': 'hawaiian', 'iw': 'hebrew', 'hi': 'hindi', 'hmn': 'hmong', 'hu': 'hungarian', 'is': 'icelandic', 'ig': 'igbo', 'id': 'indonesian', 'ga': 'irish', 'it': 'italian', 'ja': 'japanese', 'jw': 'javanese', 'kn': 'kannada', 'kk': 'kazakh', 'km': 'khmer', 'ko': 'korean', 'ku': 'kurdish (kurmanji)', 'ky': 'kyrgyz', 'lo': 'lao', 'la': 'latin', 'lv': 'latvian', 'lt': 'lithuanian', 'lb': 'luxembourgish', 'mk': 'macedonian', 'mg': 'malagasy', 'ms': 'malay', 'ml': 'malayalam', 'mt': 'maltese', 'mi': 'maori', 'mr': 'marathi', 'mn': 'mongolian', 'my': 'myanmar (burmese)', 'ne': 'nepali', 'no': 'norwegian', 'ps': 'pashto', 'fa': 'persian', 'pl': 'polish', 'pt': 'portuguese', 'pa': 'punjabi', 'ro': 'romanian', 'ru': 'russian', 'sm': 'samoan', 'gd': 'scots gaelic', 'sr': 'serbian', 'st': 'sesotho', 'sn': 'shona', 'sd': 'sindhi', 'si': 'sinhala', 'sk': 'slovak', 'sl': 'slovenian', 'so': 'somali', 'es': 'spanish', 'su': 'sundanese', 'sw': 'swahili', 'sv': 'swedish', 'tg': 'tajik', 'ta': 'tamil', 'te': 'telugu', 'th': 'thai', 'tr': 'turkish', 'uk': 'ukrainian', 'ur': 'urdu', 'uz': 'uzbek', 'vi': 'vietnamese', 'cy': 'welsh', 'xh': 'xhosa', 'yi': 'yiddish', 'yo': 'yoruba', 'zu': 'zulu', 'fil': 'Filipino', 'he': 'Hebrew'}

class BookTranslator:
    def __init__(self, batch_size=5, progress_callback=None, src_lang='en', dest_lang='pt'):
        self.batch_size = batch_size
        self.origin_book = None
        self.epub_name = None
        self.progress_callback = progress_callback
        self.src_lang = src_lang
        self.dest_lang = dest_lang

    def translate_text(self, texts):
        translations = []
        for text in texts:
            try:
                translator = Translator()
                result = translator.translate(f"{text}", src=self.src_lang, dest=self.dest_lang)
                translation = result.text
                translations.append(translation)
                print(f"Translated text: {text[:30]}... -> {translation[:30]}...")
            except Exception as e:
                print(f"Failed to translate text: {text[:30]}... Error: {str(e)}")
                translations.append(text)  # If translation fails, keep original text
        return translations

    def translate_book(self, epub_file_path):
        print(f"Starting translation of book: {epub_file_path}")
        self.origin_book = epub.read_epub(epub_file_path)
        new_book = epub.EpubBook()
        new_book.metadata = self.origin_book.metadata
        new_book.spine = self.origin_book.spine
        new_book.toc = self.origin_book.toc
        batch_p = []
        batch_original_texts = []
        batch_count = 0

        items = list(self.origin_book.get_items())  # Convert the generator to a list
        total_items = len(items)
        processed_items = 0

        for i in items:
            if i.get_type() == ebooklib.ITEM_DOCUMENT:
                try:
                    soup = bs(i.get_body_content(), "html.parser")
                    p_list = soup.findAll("p")

                    if not p_list:
                        print(f"No paragraphs found in document item, skipping.")
                        continue

                    for p in p_list:
                        if p and p.text and not p.text.isdigit():
                            batch_p.append(p)
                            batch_original_texts.append(p.text)
                            batch_count += 1

                            if batch_count == self.batch_size:
                                print(f"Translating batch of {self.batch_size} texts.")
                                translated_batch = self.translate_text(batch_original_texts)
                                for j, c_p in enumerate(batch_p):
                                    c_p.string = translated_batch[j]

                                batch_p = []
                                batch_original_texts = []
                                batch_count = 0

                    if batch_p:
                        print(f"Translating final batch of {batch_count} texts.")
                        translated_batch = self.translate_text(batch_original_texts)
                        for j, c_p in enumerate(batch_p):
                            c_p.string = translated_batch[j]

                        batch_p = []
                        batch_original_texts = []
                        batch_count = 0

                    i.content = soup.prettify().encode()
                except Exception as e:
                    print(f"Failed to process document item: {str(e)}")
                    continue
            new_book.add_item(i)

            processed_items += 1
            if self.progress_callback:
                progress = int((processed_items / total_items) * 100)
                self.progress_callback(progress)

        self.epub_name = os.path.splitext(os.path.basename(epub_file_path))[0]
        output_path = f"{self.epub_name}_translated.epub"
        epub.write_epub(output_path, new_book, {})

        # Create translated_books directory if it doesn't exist
        translated_books_dir = os.path.join(os.getcwd(), "translated_books")
        if not os.path.exists(translated_books_dir):
            os.makedirs(translated_books_dir)

        # Move the translated book to the translated_books directory
        final_output_path = os.path.join(translated_books_dir, output_path)
        shutil.move(output_path, final_output_path)

        print(f"EPUB translated and moved to {final_output_path}")
        return final_output_path


def traduzir_livro():
    try:
        arquivo = filedialog.askopenfilename(filetypes=[("EPUB files", "*.epub")])
        if not arquivo:
            return

        src_lang = src_lang_var.get().split(' ')[-1].strip('()')
        dest_lang = dest_lang_var.get().split(' ')[-1].strip('()')

        print(f"Selected source language: {src_lang}, target language: {dest_lang}")

        translator = BookTranslator(batch_size=5, progress_callback=atualizar_progresso, src_lang=src_lang, dest_lang=dest_lang)
        translated_file_path = translator.translate_book(arquivo)

        label_status.config(text="Seu livro foi traduzido com sucesso!")
        btn_abrir_pasta.pack(pady=10)
        btn_nova_traducao.pack(pady=10)

        # Update the abrir_pasta button to open the translated_books directory
        btn_abrir_pasta.config(command=lambda: abrir_pasta(os.path.join(os.getcwd(), "translated_books")))

    except Exception as e:
        label_status.config(text="Falha na tradução.")
        print(f"Translation failed: {str(e)}")
        messagebox.showerror("Erro", f"Falha na tradução: {str(e)}")
    finally:
        progresso.pack_forget()

def iniciar_traducao():
    btn_traduzir.pack_forget()
    progresso.pack(pady=20)
    threading.Thread(target=traduzir_livro).start()

def atualizar_progresso(value):
    progresso['value'] = value
    root.update_idletasks()

def abrir_pasta(directory):
    if platform.system() == "Windows":
        os.startfile(directory)
    elif platform.system() == "Darwin":  # macOS
        subprocess.Popen(["open", directory])
    else:  # Linux and other Unix-like systems
        subprocess.Popen(["xdg-open", directory])

def nova_traducao():
    # Reset the UI to the original state
    label_status.config(text="")
    btn_abrir_pasta.pack_forget()
    btn_nova_traducao.pack_forget()
    progresso.pack_forget()
    btn_traduzir.pack(pady=20)

root = tk.Tk()
root.title("Tradutor EPUB")
root.geometry("400x300")
root.resizable(False, False)
root.eval('tk::PlaceWindow . center')

# Language selection
src_lang_var = tk.StringVar(value='english (en)')
dest_lang_var = tk.StringVar(value='portuguese (pt)')

langs_sorted = sorted(LANGUAGES.keys())

label_src_lang = tk.Label(root, text="Idioma de Origem:", font=("Helvetica", 12))
label_src_lang.pack(pady=5)
combobox_src_lang = ttk.Combobox(root, textvariable=src_lang_var, values=[f"{LANGUAGES[lang]} ({lang})" for lang in langs_sorted], state="readonly", font=("Helvetica", 10))
combobox_src_lang.pack(pady=5)

label_dest_lang = tk.Label(root, text="Idioma de Destino:", font=("Helvetica", 12))
label_dest_lang.pack(pady=5)
combobox_dest_lang = ttk.Combobox(root, textvariable=dest_lang_var, values=[f"{LANGUAGES[lang]} ({lang})" for lang in langs_sorted], state="readonly", font=("Helvetica", 10))
combobox_dest_lang.pack(pady=5)

# Estilizando o botão de traduzir
btn_traduzir = tk.Button(root, text="Traduzir EPUB", command=iniciar_traducao, font=("Helvetica", 14), bg="#4CAF50", fg="white")
btn_traduzir.pack(pady=20)

label_status = tk.Label(root, text="", font=("Helvetica", 12))
label_status.pack(pady=10)

progresso = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progresso.pack_forget()

# Button to open the folder where translated books are stored
btn_abrir_pasta = tk.Button(root, text="Abrir pasta de livros traduzidos", font=("Helvetica", 14), bg="#2196F3", fg="white")
btn_abrir_pasta.pack_forget()

# Button to start a new translation
btn_nova_traducao = tk.Button(root, text="Nova Tradução", command=nova_traducao, font=("Helvetica", 14), bg="#FF5722", fg="white")
btn_nova_traducao.pack_forget()

root.mainloop()
