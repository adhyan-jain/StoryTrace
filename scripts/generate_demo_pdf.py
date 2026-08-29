import os
from fpdf import FPDF

def create_screenplay():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Page 1
    pdf.add_page()
    pdf.set_font("Courier", size=12)
    
    pdf.cell(0, 10, "INT. WAREHOUSE - NIGHT", ln=True)
    pdf.cell(0, 10, "", ln=True)
    pdf.multi_cell(0, 5, "JOHN (40s), battered but determined, stands in the middle of a dusty warehouse. He pulls out a SILVER PISTOL.")
    pdf.cell(0, 10, "", ln=True)
    pdf.cell(0, 5, "                          JOHN", ln=True)
    pdf.cell(0, 5, "            It ends tonight.", ln=True)
    pdf.cell(0, 10, "", ln=True)
    
    pdf.cell(0, 10, "EXT. STREET - DAY", ln=True)
    pdf.cell(0, 10, "", ln=True)
    pdf.multi_cell(0, 5, "John walks down the busy street. A visible BANDAGE is wrapped around his right hand.")
    pdf.cell(0, 10, "", ln=True)
    
    # Page 2
    pdf.add_page()
    pdf.cell(0, 10, "INT/EXT. CAR - CONTINUOUS", ln=True)
    pdf.cell(0, 10, "", ln=True)
    pdf.multi_cell(0, 5, "John starts the engine. He tosses the gun onto the passenger seat.")
    pdf.cell(0, 10, "", ln=True)
    
    pdf.cell(0, 10, "INT. APARTMENT - NIGHT", ln=True)
    pdf.cell(0, 10, "", ln=True)
    pdf.multi_cell(0, 5, "John sits on the couch. He removes the bandage. The hand is healed.")
    pdf.cell(0, 10, "", ln=True)
    
    pdf.cell(0, 10, "EXT. ALLEYWAY - NIGHT", ln=True)
    pdf.cell(0, 10, "", ln=True)
    pdf.multi_cell(0, 5, "John raises the silver pistol. Where did he get it?")
    pdf.cell(0, 10, "", ln=True)

    # Ensure demo directory exists
    os.makedirs("demo", exist_ok=True)
    
    pdf.output("demo/screenplay.pdf")
    print("Created demo/screenplay.pdf")

if __name__ == "__main__":
    create_screenplay()
