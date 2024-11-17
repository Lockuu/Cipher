import os
from tkinter import Tk, PanedWindow, Frame, Label, Button, messagebox, filedialog, Text
from tkinter.ttk import Style
from fpdf import FPDF
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter
from PyPDF2 import PdfReader, PdfWriter
import wave

# Functionality: Image Analysis
def extract_text_from_image(image_path):
    image = Image.open(image_path)
    binary_message_lsb = ""
    binary_message_msb = ""

    width, height = image.size
    pixels = image.getdata()

    for pixel_index, pixel in enumerate(pixels):
        if pixel_index >= 10000:
            break
        for channel in range(3):
            binary_message_lsb += str(pixel[channel] & 1)
            binary_message_msb += str((pixel[channel] >> 7) & 1)

    binary_message_lsb = binary_message_lsb[:500]
    binary_message_msb = binary_message_msb[:500]

    def binary_to_text(binary_data):
        message = ""
        for i in range(0, len(binary_data), 8):
            byte = binary_data[i:i + 8]
            if len(byte) == 8:
                char = chr(int(byte, 2))
                if char.isprintable():
                    message += char
        return message.strip()

    message_lsb = binary_to_text(binary_message_lsb) or "No readable text found in LSB."
    message_msb = binary_to_text(binary_message_msb) or "No readable text found in MSB."

    return message_lsb, message_msb

def extract_data_from_image(image_path):
    """Extract hidden metadata from image."""
    try:
        image = Image.open(image_path)
        metadata = image.info
        if "HiddenData" in metadata:
            return metadata["HiddenData"]
        else:
            raise ValueError("No hidden data found in the image metadata.")
    except Exception as e:
        raise ValueError(f"Error extracting data from image: {e}")

def save_data_to_pdf(data, output_pdf_path):
    """Save extracted data to a PDF file."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, data)
        pdf.output(output_pdf_path)
        messagebox.showinfo("Success", f"Data saved to PDF: {output_pdf_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error saving to PDF: {e}")

def find_watermark_without_cv2(image_path):
    try:
        img = Image.open(image_path).convert("L")
        enhanced_img = ImageEnhance.Contrast(img).enhance(2.0)
        edges = enhanced_img.filter(ImageFilter.FIND_EDGES)

        draw = ImageDraw.Draw(edges)
        width, height = edges.size
        pixel_data = edges.load()

        for x in range(0, width, 10):
            for y in range(0, height, 10):
                if pixel_data[x, y] > 200:
                    draw.rectangle([(x - 5, y - 5), (x + 5, y + 5)], outline=255)

        return edges, "Potential watermark regions highlighted."
    except Exception as e:
        return None, f"Error processing image: {e}"

def extract_message_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        metadata = reader.metadata

        if metadata:
            result = "Metadata found in PDF:\n"
            for key, value in metadata.items():
                result += f"{key}: {value}\n"
            if '/Message' in metadata:
                result += f"\nHidden message found: {metadata['/Message']}"
            else:
                result += "\nNo hidden message found."
        else:
            result = "No metadata found in PDF."

        return result
    except Exception as e:
        return f"Error in extracting PDF metadata: {e}"

def remove_metadata_from_pdf(pdf_path, save_path):
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        writer.add_metadata({})  # Reset metadata

        for page in reader.pages:
            writer.add_page(page)

        cleaned_pdf_path = os.path.join(save_path, "Cleaned_PDF.pdf")
        with open(cleaned_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)

        return cleaned_pdf_path
    except Exception as e:
        return f"Error in removing metadata: {e}"

def decode_text_from_audio(wav_file):
    # Open the WAV file
    audio = wave.open(wav_file, 'rb')
    params = audio.getparams()
    frames = audio.readframes(params.nframes)
    
    # Extract the least significant bits from the audio frames
    binary_data = ''
    for byte in frames:
        binary_data += str(byte & 1)
    
    # Convert the binary data back to text
    decoded_text = ''.join(chr(int(binary_data[i:i+8], 2)) for i in range(0, len(binary_data), 8))
    return decoded_text

def save_text_to_pdf(text, output_pdf):
    # Create a PDF object
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    # Add a page
    pdf.add_page()
    # Set font
    pdf.set_font("Arial", size=12)
    # Add decoded text to the PDF
    pdf.multi_cell(0, 10, text)  # `multi_cell` automatically handles line breaks
    # Save the PDF to the output file
    pdf.output(output_pdf)

# Main GUI Application
class CombinedGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CIPHER SCAN")
        self.root.geometry("1200x600")
        self.root.configure(bg="#f0f0f0")  # Light gray background

        self.is_night_light = False

        # Full-screen and Minimize
        self.root.bind("<F11>", lambda event: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda event: self.exit_fullscreen())

        paned_window = PanedWindow(root, orient="horizontal", bg="#d9d9d9")  # Slightly darker split background
        paned_window.pack(fill="both", expand=True)
        

        # Image Analysis GUI
        frame1 = Frame(paned_window, bg="#ffffff", bd=2, relief="groove")  # White frame for lighter contrast
        paned_window.add(frame1)
        self.setup_image_analysis_gui(frame1)

        # PDF Metadata Analysis GUI
        frame2 = Frame(paned_window, bg="#ffffff", bd=2, relief="groove")
        paned_window.add(frame2)
        self.setup_pdf_analysis_gui(frame2)

        # Watermark Detection GUI (Section 3)
        frame3 = Frame(paned_window, bg="#ffffff", bd=2, relief="groove")
        paned_window.add(frame3)
        self.setup_watermark_detection_gui(frame3)

        #audio detection gui (section 4)
        frame4 = Frame(paned_window, bg="#ffffff", bd=2, relief="groove")
        paned_window.add(frame4)
        self.setup_audio_analysis_gui(frame4)

        self.toggle_button = Button(root, text="🌙 Switch to Night Light Mode", command=self.toggle_mode, font=("Arial", 12), relief="flat", bd=1, bg="#4a90e2", fg="white")
        self.toggle_button.pack(side="bottom", pady=10)

        self.exit_button = Button(root, text="Exit", command=self.exit_app, font=("Arial", 12), relief="raised", bg="#e74c3c", fg="white")
        self.exit_button.pack(side="bottom", pady=10)

    def setup_audio_analysis_gui(self, frame):
        Label(frame, text="Audio Analysis", font=("Arial", 20, 'bold'), bg="#ffffff", fg="#4a90e2").pack(pady=10)
        Label(frame, text="*.wav file only", font=("Arial", 10, "italic"), bg="#ffffff").pack(pady=5)
        self.audio_path = None
        self.create_button(frame, "Choose Audio", self.choose_audio).pack(pady=10)
        self.create_button(frame, "Run Audio Analysis", self.run_audio_analysis).pack(pady=10)
        
        self.audio_result_text = Text(frame, wrap="word", height=15, width=40, bg="#f9f9f9", fg="#333333", relief="flat")
        self.audio_result_text.pack(pady=10)

    def choose_audio(self):
        self.audio_path = filedialog.askopenfilename(filetypes=[("WAV Files", "*.wav")])
        self.audio_result_text.insert("end", f"Selected Audio: {self.audio_path}\n")

    def run_audio_analysis(self):
        if not self.audio_path:
            messagebox.showerror("Error", "Please select an audio file!")
            return
        
        try:
            decoded_text = decode_text_from_audio(self.audio_path)
            self.audio_result_text.insert("end", f"Decoded Text: {decoded_text}\n")
            
            # Ask for PDF save location
            output_pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
            if output_pdf_path:
                save_text_to_pdf(decoded_text, output_pdf_path)
                messagebox.showinfo("Success", f"Decoded text saved to PDF: {output_pdf_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error during audio analysis: {str(e)}")



    def setup_image_analysis_gui(self, frame):
        Label(frame, text="Image Analysis", font=("Arial", 20, 'bold'), bg="#ffffff", fg="#4a90e2").pack(pady=10)
        self.image_path = None

        self.create_button(frame, "Choose Image", self.choose_image).pack(pady=10)
        self.create_button(frame, "Run Analysis", self.run_image_analysis).pack(pady=10)
        Label(frame, text="*.png image only", font=("Arial", 10, "italic"), bg="#ffffff").pack(pady=5)
        self.create_button(frame, "Detect QR", self.extract_image_metadata).pack(pady=10)
        
        self.image_result_text = Text(frame, wrap="word", height=15, width=40, bg="#f9f9f9", fg="#333333", relief="flat")
        self.image_result_text.pack(pady=10)

    def choose_image(self):
        self.image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        self.image_result_text.insert("end", f"Selected Image: {self.image_path}\n")

    def extract_image_metadata(self):
        """Extract hidden metadata from image and save it to PDF."""
        if not self.image_path:
            messagebox.showerror("Error", "Please select an image first!")
            return

        try:
            hidden_data = extract_data_from_image(self.image_path)
            self.image_result_text.insert("end", f"Hidden Data: {hidden_data}\n")

            # Ask for PDF save location
            output_pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
            if output_pdf_path:
                save_data_to_pdf(hidden_data, output_pdf_path)

        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def run_image_analysis(self):
        if not self.image_path:
            return
        lsb_message, msb_message = extract_text_from_image(self.image_path)
        self.image_result_text.insert("end", f"LSB: {lsb_message}\nMSB: {msb_message}\n")

    def setup_pdf_analysis_gui(self, frame):
        Label(frame, text="PDF Metadata Analysis", font=("Arial", 20, 'bold'), bg="#ffffff", fg="#4a90e2").pack(pady=10)
        self.pdf_path = None

        self.create_button(frame, "Choose PDF", self.choose_pdf).pack(pady=10)
        self.create_button(frame, "Analyze PDF", self.run_pdf_analysis).pack(pady=10)
        self.create_button(frame, "Remove Metadata", self.remove_pdf_metadata).pack(pady=10)

        self.pdf_result_text = Text(frame, wrap="word", height=15, width=40, bg="#f9f9f9", fg="#333333", relief="flat")
        self.pdf_result_text.pack(pady=10)

    def setup_watermark_detection_gui(self, frame):
        Label(frame, text="Watermark Detection", font=("Arial", 20, 'bold'), bg="#ffffff", fg="#4a90e2").pack(pady=10)
        self.watermark_image_path = None

        self.create_button(frame, "Choose Image", self.choose_watermark_image).pack(pady=10)
        self.create_button(frame, "Detect Watermark", self.detect_watermark).pack(pady=10)

        self.watermark_result_text = Text(frame, wrap="word", height=15, width=40, bg="#f9f9f9", fg="#333333", relief="flat")
        self.watermark_result_text.pack(pady=10)

    def choose_watermark_image(self):
        self.watermark_image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        self.watermark_result_text.insert("end", f"Selected Image: {self.watermark_image_path}\n")

    def detect_watermark(self):
        if not self.watermark_image_path:
            messagebox.showerror("Error", "Please select an image file!")
            return

        processed_image, message = find_watermark_without_cv2(self.watermark_image_path)

        if processed_image is not None:
            save_path = os.path.join(os.path.dirname(self.watermark_image_path), "watermarked_detected.png")
            processed_image.save(save_path)
            self.watermark_result_text.insert("end", f"{message}\nWatermarked image saved at: {save_path}\n")
            processed_image.show()
    
    def create_button(self, frame, text, command):
        button = Button(frame, text=text, command=command, font=("Arial", 12), bg="#e6e6e6", fg="#000000", bd=1, relief="raised", activebackground="#d0d0d0")
        button.bind("<Enter>", lambda e: self.on_hover(button))
        button.bind("<Leave>", lambda e: self.on_leave(button))
        button.config(highlightthickness=0, highlightbackground="#aaaaaa", relief="solid")
        return button

    def on_hover(self, button):
        button.config(bg="#d0d0d0", relief="groove", activebackground="#b0b0b0")

    def on_leave(self, button):
        button.config(bg="#e6e6e6", relief="raised", activebackground="#d0d0d0")

    
    def toggle_mode(self):
        """Switch to Night Light mode."""
        if self.is_night_light:
            self.set_light_mode()
        else:
            self.set_night_light_mode()

    def set_night_light_mode(self):
        """Switch to night light mode with warm colors."""
        self.is_night_light = True
        self.root.configure(bg="#FFFAF0")  # Warm, light yellowish background
        self.toggle_button.configure(bg="#FFCC99", fg="black")
        self.update_frames_and_buttons("#FFFAF0", "#000000", "#FFCC99")
        self.toggle_button.config(text="🌞 Switch to Light Mode")  # Sun emoji for light mode

    def set_light_mode(self):
        """Switch back to light mode with default colors."""
        self.is_night_light = False
        self.root.configure(bg="#f0f0f0")
        self.toggle_button.configure(bg="#4a90e2", fg="white")
        self.update_frames_and_buttons("#ffffff", "#000000", "#4a90e2")
        self.toggle_button.config(text="🌙 Switch to Night Light Mode")  # Moon emoji for night light mode
        self.toggle_button.config(state="normal")  # Enable button again


    def update_frames_and_buttons(self, frame_bg, text_fg, button_fg):
        """Update frame and button colors based on selected mode."""
        for widget in self.root.winfo_children():
            if isinstance(widget, Frame):
                widget.configure(bg=frame_bg)
                for child in widget.winfo_children():
                    if isinstance(child, Label):
                        child.configure(bg=frame_bg, fg=text_fg)
                    if isinstance(child, Button):
                        child.configure(bg=button_fg, fg=text_fg)
            elif isinstance(widget, PanedWindow):
                widget.configure(bg=frame_bg)
                for child in widget.winfo_children():
                    child.configure(bg=frame_bg)
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, Label):
                            grandchild.configure(bg=frame_bg, fg=text_fg)
                        elif isinstance(grandchild, Button):
                            grandchild.configure(bg=button_fg, fg=text_fg)


    def toggle_fullscreen(self):
        self.root.attributes("-fullscreen", True)

    def exit_fullscreen(self):
        self.root.attributes("-fullscreen", False)
   

    

    def choose_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        self.pdf_result_text.insert("end", f"Selected PDF: {self.pdf_path}\n")

    def run_pdf_analysis(self):
        if not self.pdf_path:
            return
        findings = extract_message_from_pdf(self.pdf_path)
        self.pdf_result_text.insert("end", findings)

    def remove_pdf_metadata(self):
        if not self.pdf_path:
            messagebox.showerror("Error", "Please select a PDF file!")
            return

        save_dir = filedialog.askdirectory(title="Select Save Location")
        if not save_dir:
            messagebox.showerror("Error", "Please select a directory to save the cleaned PDF.")
            return

        cleaned_pdf_path = remove_metadata_from_pdf(self.pdf_path, save_dir)

        if "Error" in cleaned_pdf_path:
            self.pdf_result_text.insert("end", f"{cleaned_pdf_path}\n")
        else:
            self.pdf_result_text.insert("end", f"Metadata removed successfully. Cleaned PDF saved at: {cleaned_pdf_path}\n")
            messagebox.showinfo("Success", f"Cleaned PDF saved at: {cleaned_pdf_path}")

    def toggle_fullscreen(self):
        self.root.attributes("-fullscreen", True)

    def exit_fullscreen(self):
        self.root.attributes("-fullscreen", False)

    def exit_app(self):
        """Exit the application."""
        self.root.quit()

if __name__ == "__main__":
    root = Tk()
    app = CombinedGUI(root)
    root.mainloop()

