import streamlit as st
import pdfplumber
from PIL import Image
import pytesseract
import io
import re
import pandas as pd

# Configure pytesseract path if necessary (e.g., if tesseract is not in PATH)
# For Colab, you might need to install tesseract-ocr first: !apt install tesseract-ocr
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' # Adjust path for your system/Colab

st.set_page_config(layout="wide", page_title="Data Extraction App")
st.title("Document Data Extractor")

def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_text_from_image(uploaded_file):
    image = Image.open(uploaded_file)
    text = pytesseract.image_to_string(image)
    return text

def parse_transactions(text):
    transactions = []
    lines = text.split('\n')

    # More robust regex patterns for dates and amounts
    # Date patterns: MM/DD/YYYY, MM-DD-YYYY, MM/DD/YY, Month DD, YYYY, DD Mon YYYY, etc.
    date_patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YY
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b', # Month DD, YYYY or Mon DD
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b' # DD Month YYYY
    ]

    # Amount patterns: handles positive/negative, currency symbols, thousands commas, two decimal places
    amount_pattern = r'(-?\s*\$?(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d{2})?)'

    for line in lines:
        line = line.strip()
        if not line:
            continue

        found_date = None
        for dp in date_patterns:
            date_match = re.search(dp, line, re.IGNORECASE)
            if date_match:
                found_date = date_match.group(0).strip()
                line_without_date = line.replace(found_date, '', 1).strip() # Remove the first occurrence of date
                break

        if found_date:
            amount_match = re.search(amount_pattern, line_without_date)
            if amount_match:
                amount = amount_match.group(1).strip()
                description = line_without_date.replace(amount, '', 1).strip()

                # Clean up description - remove extra spaces, symbols etc.
                description = re.sub(r'\s+', ' ', description).strip()

                transactions.append({"Date": found_date, "Description": description, "Amount": amount})
            else:
                # Case where date is found but no clear amount, maybe description contains numbers
                pass
        # More complex parsing for lines without clear date-amount structure might be needed here

    return pd.DataFrame(transactions) if transactions else pd.DataFrame(columns=["Date", "Description", "Amount"])

uploaded_file = st.file_uploader("Upload a PDF or Image file", type=["pdf", "png", "jpg", "jpeg"])

if st.button("Extract Data"):
    if uploaded_file is not None:
        with st.spinner("Extracting and parsing data..."):
            file_type = uploaded_file.type
            extracted_text = ""

            if "pdf" in file_type:
                try:
                    extracted_text = extract_text_from_pdf(uploaded_file)
                    st.success("Text extracted from PDF!")
                except Exception as e:
                    st.error(f"Error extracting text from PDF: {e}")
                    st.info("Attempting OCR for PDF (might be a scanned document). This can take a while...")
                    # Placeholder for robust scanned PDF handling (requires pdf2image etc.)
                    st.warning("Direct OCR on PDF bytes is not straightforward without converting to image first. Please convert scanned PDFs to images before uploading for OCR.")
                    extracted_text = "(OCR attempt placeholder for scanned PDF - requires pdf2image library and more complex logic)"

            elif "image" in file_type or "png" in file_type or "jpg" in file_type or "jpeg" in file_type:
                try:
                    extracted_text = extract_text_from_image(uploaded_file)
                    st.success("Text extracted from image using OCR!")
                except Exception as e:
                    st.error(f"Error extracting text from image: {e}")
            else:
                st.warning("Unsupported file type. Please upload a PDF or an image.")

            if extracted_text and extracted_text != "(OCR attempt placeholder for scanned PDF - requires pdf2image library and more complex logic)":
                st.subheader("Extracted Raw Text:")
                st.text_area("", extracted_text, height=300)

                st.subheader("Extracted Transactions:")
                transactions_df = parse_transactions(extracted_text)
                if not transactions_df.empty:
                    st.dataframe(transactions_df)
                    st.write(f"{len(transactions_df)} transactions found.")
                    csv = transactions_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Extracted Data as CSV",
                        data=csv,
                        file_name="extracted_transactions.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No transactions found with the current parsing rules.")
            else:
                st.info("No text extracted or an error occurred.")

    else:
        st.warning("Please upload a file first.")
