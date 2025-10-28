import os
from docx2pdf import convert
from shutil import which

# Define the directory where your .docx reports are located
REPORTS_DIR = "./reports"
# Define a new directory for the PDF outputs
PDF_REPORTS_DIR = "./pdf_reports"

# --- IMPORTANT: Configure LibreOffice executable path for Linux ---
# This path should now be supported by an upgraded docx2pdf.
# Try to auto-detect first.
LIBREOFFICE_PATH = which("soffice") or "/usr/bin/soffice"
# If 'soffice' isn't found by 'which', you might need to manually set it like:
# LIBREOFFICE_PATH = "/opt/libreoffice7.6/program/soffice" # Example for a specific LibreOffice version

if __name__ == "__main__":
    # Ensure the PDF output directory exists
    os.makedirs(PDF_REPORTS_DIR, exist_ok=True)

    print(f"Starting conversion of .docx files from '{REPORTS_DIR}' to .pdf in '{PDF_REPORTS_DIR}'...")

    # Check if the determined LibreOffice path actually exists
    if not LIBREOFFICE_PATH or not os.path.exists(LIBREOFFICE_PATH):
        print(f"Error: LibreOffice executable not found at '{LIBREOFFICE_PATH if LIBREOFFICE_PATH else 'the configured path'}'.")
        print("Please ensure LibreOffice is installed and update 'LIBREOFFICE_PATH' in the script to its correct location.")
        exit(1) # Exit if LibreOffice is not found

    # Iterate through all files in the reports directory
    for filename in os.listdir(REPORTS_DIR):
        if filename.endswith(".docx"):
            docx_file_path = os.path.join(REPORTS_DIR, filename)
            pdf_filename = filename.replace(".docx", ".pdf")
            pdf_file_path = os.path.join(PDF_REPORTS_DIR, pdf_filename)

            try:
                print(f"Converting '{filename}' to PDF using executable '{LIBREOFFICE_PATH}'...")
                # Pass the executable path to the convert function
                convert(docx_file_path, pdf_file_path, executable=LIBREOFFICE_PATH)
                print(f"Successfully converted '{filename}' to '{pdf_filename}'.")
            except Exception as e:
                print(f"Error converting '{filename}': {e}")
                print("This usually means LibreOffice encountered an issue during conversion.")
                print("Check the .docx file for corruption or complex elements that LibreOffice might struggle with.")
                print(f"Ensure LibreOffice can open '{docx_file_path}' manually without errors.")
    
    print("Conversion process finished.")
    if not os.listdir(PDF_REPORTS_DIR):
        print("No PDF files were generated. Check for errors above or ensure .docx files exist in the reports directory.")