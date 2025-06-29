import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

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

    for line in full_text.split("\n"):
        if "Beneficiary Name" in line:
            parts = line.split(":")
            if len(parts) > 1:
                client_name = parts[1].strip().split("/")[-1].strip()
        if "Member Of" in line:
            parts = line.split(":")
            if len(parts) > 1:
                insurance_company = parts[1].strip()
        if "Dispensed Date" in line:
            parts = line.split(":")
            if len(parts) > 1:
                dispensed_date = parts[1].strip()

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

        df["Qty"] = df["Qty"].str.extract(r"(\d+\.?\d*)").astype(float)
        df["Unit"] = df["Unit"].str.extract(r"(\d+\.?\d*)").astype(float)
        df["اسم الصنف"] = df["Name"]
        df["الكمية"] = df["Qty"]
        df["سعر الوحدة"] = df["Unit"]
        df["سعر الكمية"] = (df["Qty"] * df["Unit"]).round(2)

        final_df = df[["اسم الصنف", "الكمية", "سعر الوحدة", "سعر الكمية"]]

        st.success(f"✅ تم استخراج {len(final_df)} صنف معتمد")
        st.dataframe(final_df)

        # زر تحميل Excel
        output = BytesIO()
        final_df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="⬇️ تحميل Excel",
            data=output,
            file_name="approved_meds.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # توليد PDF
        if st.button("📄 توليد إيصال PDF"):
            class PDF(FPDF):
                def header(self):
                    pdf.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
                    self.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
                    self.set_fill_color(230, 230, 230)
                    self.image("logo.png", x=10, y=8, w=20)
                    self.set_font("Amiri", "B", 14)
                    self.cell(0, 10, reshape_arabic("صيدلية د/ روماني عاطف يوسف"), ln=1, align="C")
                    self.set_font("Amiri", "", 10)
                    self.cell(0, 10, reshape_arabic("العنوان: أسيوط - الفتح - عزبة التحرير - شارع رقم 1"), ln=1, align="C")
                    self.cell(0, 10, reshape_arabic("تليفون: 01557000365"), ln=1, align="C")
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
            pdf.cell(0, 10, reshape_arabic("اسم العميل: "), ln=1, align="R")
            pdf.cell(0, 10, reshape_arabic("شركة التأمين: "), ln=1, align="R")
            pdf.cell(0, 10, reshape_arabic("التاريخ: "), ln=1, align="R")
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

            for index, row in final_df.iterrows():
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
            pdf.cell(0, 10, reshape_arabic(f"عدد الأصناف: {len(final_df)}"), ln=1, align="R")
            pdf.cell(0, 10, reshape_arabic(f"الإجمالي: {final_df['سعر الكمية'].sum():.2f} EGP"), ln=1, align="R")

            pdf_output = pdf.output(dest='S')
            pdf_buffer = BytesIO(pdf_output)
 

            import os
            base_name = os.path.splitext(uploaded_file.name)[0]
            output_name = f"{base_name}_receipt.pdf"
            st.download_button(label="⬇️ تحميل إيصال PDF",data=pdf_buffer,file_name=output_name,mime="application/pdf")

    else:
        st.error("❌ لم يتم العثور على جدول يحتوي على عمود 'Qty'.")




































