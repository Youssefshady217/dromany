import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

def reshape_arabic(text):
    return get_display(arabic_reshaper.reshape(str(text)))

VALID_USERNAME = "romany"
VALID_PASSWORD = "1234"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# شاشة تسجيل الدخول
if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول")

    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        login = st.form_submit_button("دخول")

        if login:
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                st.session_state.logged_in = True
                st.success("✅ تم تسجيل الدخول بنجاح")
                st.rerun()
            else:
                st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")

    st.stop()

st.set_page_config(page_title="صيدلية د/ روماني", layout="centered")
st.title("د/روماني عاطف يوسف")


uploaded_file = st.file_uploader("📤 ارفع ملف PDF يحتوي على جدول", type=["pdf"])

def reshape_arabic(text):
    return get_display(arabic_reshaper.reshape(str(text)))

if uploaded_file:
    # قراءة النص الكامل لاستخراج بيانات العميل
    with pdfplumber.open(uploaded_file) as pdf:
        full_text = ""
        table_data = []
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    table_data.append(row)
                    

    # استخراج البيانات الأساسية
    client_name = ""
    insurance_company = ""
    dispensed_date = ""

    import re

    for line in full_text.split("\n"):
        if "Beneficiary Name" in line:# محاولة استخراج الاسم مباشرة باستخدام regex بعد النقطتين وبعد الشرطة المائلة
            match = re.search(r"Beneficiary Name\s*:\s*.*?/\s*(.+)", line)
            if match:
                client_name = match.group(1).strip()
                client_name = client_name[::-1]


        if "Member Of" in line:
            parts = line.split(":")
            if len(parts) > 1:
                after_text = parts[1].strip()
                words = after_text.split()

                if words and words[0].lower() == "claim":
                    insurance_company = "صندوق تحسين أحوال العاملين بالجامعات الحكومية - العاملين بجامعة أسيوط"
                elif "Claim" in words:
                    claim_index = words.index("Claim")
                    insurance_company = " ".join(words[:claim_index])
                    insurance_company = insurance_company[::-1]
                else:
                    insurance_company = after_text

        if "Dispensed Date" in line:
            match = re.search(r"Dispensed Date\s*:\s*(\d{2}/\d{2}/\d{4})", line)
            if match:
                dispensed_date = match.group(1)

    df = pd.DataFrame(table_data)
    


    # محاولة تحديد رأس الجدول
    header_row_index = None
    for i, row in df.iterrows():
        if any("Qty" in str(cell) for cell in row):
            header_row_index = i
            break

    if header_row_index is not None:
        df.columns = df.iloc[header_row_index]
        df = df.drop(index=range(0, header_row_index + 1)).reset_index(drop=True)
        df = df[df["Status"].str.contains("Approved", na=False)]
        df = df.fillna("")
        
        df["Dis."] = df["Dis."].astype(str).str.replace("\n","").str.strip()
        df["Cop."] = df["Cop."].astype(str).str.replace("\n","").str.strip()
        df["Net"] = df["Net"].astype(str).str.replace("\n","").str.strip()
        

        df["اسم الصنف"] = df["Name"]
        df["الكمية"] = df["Qty"]
        df["سعر الوحدة"] = df["Unit"]
        df[["Dis.","Cop.","Net"]] = df[["Dis.","Cop.","Net"]].apply(pd.to_numeric, errors="coerce")
        df["سعر الكمية"] = (df["Dis."] + df["Cop."] + df["Net"]).round(2)

        final_df = df[["اسم الصنف", "الكمية", "سعر الوحدة", "سعر الكمية"]]
        


        st.success(f"✅ تم استخراج {len(final_df)} صنف معتمد")
        edited_df = st.data_editor(final_df, num_rows="dynamic", use_container_width=True)


        # زر تحميل Excel
        output = BytesIO()
        edited_df.to_excel(output, index=False)
        output.seek(0)


        

        # توليد PDF
        if st.button("📄 توليد إيصال PDF"):
            class PDF(FPDF):
                def header(self):
                    pdf.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
                    self.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
                    self.set_fill_color(230, 230, 230)
                    self.image("logo.png", x=10, y=8, w=20)
                    self.set_font("Amiri", "B", 14)
                    self.cell(0, 10, reshape_arabic("صيدلية د/ نادر نبيل فهمي"), ln=1, align="C")
                    self.set_font("Amiri", "", 11)
                    self.cell(0, 10, reshape_arabic("م.ض: 01-40-181-00591-5"), ln=1, align="C")
                    self.cell(0, 10, reshape_arabic("س.ت: 94294"), ln=1, align="C")
                    self.set_font("Amiri", "", 10)
                    self.cell(0, 10, reshape_arabic("العنوان: اسيوط - شركة فريال - شارع الامام علي"), ln=1, align="C")
                    self.cell(0, 10, reshape_arabic("تليفون: 01211136366"), ln=1, align="C")
                    self.ln(5)

                def footer(self):
                    self.set_y(-20)
                    self.set_font("Amiri", "", 10)
                    self.set_text_color(100)
                    self.cell(0, 10, reshape_arabic("شكراً لتعاملكم معنا ❤"), ln=1, align="C")
                    self.cell(0, 10, reshape_arabic(f"صفحة رقم {self.page_no()}"), align="C")

            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Amiri", "", 11)

            # بيانات العميل
            reshaped_name = reshape_arabic(client_name)
            reshaped_label = reshape_arabic("اسم العميل: ")
            pdf.cell(0, 10,reshaped_name + reshaped_label , ln=1, align="R")
            pdf.cell(0, 10, reshape_arabic("شركة التأمين: " + insurance_company), ln=1, align="R")
            pdf.cell(0, 10, reshape_arabic("التاريخ: " + dispensed_date), ln=1, align="R")
            pdf.ln(5)

            # رأس الجدول
            headers = ["اسم الصنف", "الكمية", "سعر الوحدة", "سعر الكمية"]
            col_widths = [80, 25, 30, 35]
            row_height = 10
            rows_per_page = 25
            row_count = 0

            def draw_table_header():
                pdf.set_fill_color(230, 230, 230)  # رمادي فاتح لخلفية رؤوس الأعمدة
                pdf.set_font("Amiri", "B", 12)
                for i, h in enumerate(headers):
                    pdf.cell(col_widths[i], row_height, reshape_arabic(h), border=1, align="C", fill=True)
                pdf.ln()

            draw_table_header()

            for index, row in edited_df.iterrows():
                if row_count >= rows_per_page:
                    pdf.add_page()
                    draw_table_header()
                    row_count = 0

                pdf.cell(col_widths[0], row_height, reshape_arabic(row["اسم الصنف"]), border=1, align="C")
                pdf.cell(col_widths[1], row_height, reshape_arabic(row["الكمية"]), border=1, align="C")
                pdf.cell(col_widths[2], row_height, reshape_arabic(row["سعر الوحدة"]), border=1, align="C")
                pdf.cell(col_widths[3], row_height, reshape_arabic(row["سعر الكمية"]), border=1, align="C")
                pdf.ln()
                row_count += 1

            pdf.ln(5)
            pdf.cell(0, 10, reshape_arabic(f"عدد الأصناف: {len(edited_df)}"), ln=1, align="R")
            pdf.cell(0, 10, reshape_arabic(f"الإجمالي: {edited_df['سعر الكمية'].sum():.2f} EGP"), ln=1, align="R")

            pdf_output = pdf.output(dest='S')
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            pdf_buffer = BytesIO(pdf_output)
            
 

            import os
            base_name = os.path.splitext(uploaded_file.name)[0]
            output_name = f"{base_name}_receipt.pdf"
            st.download_button(label="⬇️ تحميل إيصال PDF",data=pdf_buffer,file_name=output_name,mime="application/pdf")

    else:
        st.error("❌ لم يتم العثور على جدول يحتوي على عمود 'Qty'.")




































