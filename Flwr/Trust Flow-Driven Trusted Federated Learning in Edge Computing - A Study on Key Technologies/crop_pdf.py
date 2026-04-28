import sys
from PyPDF2 import PdfReader, PdfWriter

def crop_top(input_path, output_path, trim_points=35):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    page = reader.pages[0]
    # Reduce the top of the media box and crop box
    # The default coordinate system has the origin at the bottom-left corner
    old_ur_y = page.mediabox.top
    new_ur_y = old_ur_y - trim_points
    
    page.mediabox.top = new_ur_y
    page.cropbox.top = new_ur_y
    # Optional: also adjust trimbox, bleedbox, artbox if they exist
    try:
        page.trimbox.top = new_ur_y
        page.bleedbox.top = new_ur_y
        page.artbox.top = new_ur_y
    except Exception:
        pass
        
    writer.add_page(page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"Successfully cropped {trim_points} points from top.")

if __name__ == "__main__":
    crop_top('convergence_asr.pdf', 'convergence_asr_cropped.pdf', trim_points=22)
