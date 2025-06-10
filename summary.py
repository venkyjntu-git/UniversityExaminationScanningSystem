from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.flowables import Spacer

def create_bundle_pdf(data_list, filename="bundle_report.pdf", page_size=A4):
    """
    Creates a PDF with bundle data arranged in 4 columns, 100 entries per page.
    
    Args:
        data_list: List of tuples [(bundleno, numberofscripts), ...]
        filename: Output PDF filename
        page_size: Page size (default A4)
    """
    
    # Create the PDF document
    doc = SimpleDocTemplate(filename, pagesize=page_size,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Calculate entries per column (100 entries / 4 columns = 25 rows per column)
    entries_per_page = 140
    columns = 4
    rows_per_column = entries_per_page // columns
    
    story = []
    
    # Process data in chunks of 100
    for page_start in range(0, len(data_list), entries_per_page):
        page_data = data_list[page_start:page_start + entries_per_page]
        
        # Create 4 columns of data
        table_data = []
        
        # Add headers
        headers = ['Bundle No', 'Scripts', 'Bundle No', 'Scripts', 
                  'Bundle No', 'Scripts', 'Bundle No', 'Scripts']
        table_data.append(headers)
        
        # Fill the table with data
        for row in range(rows_per_column):
            table_row = []
            for col in range(columns):
                index = col * rows_per_column + row
                if index < len(page_data):
                    bundle_no, scripts = page_data[index]
                    table_row.extend([str(bundle_no), str(scripts)])
                else:
                    table_row.extend(['', ''])  # Empty cells if no more data
            table_data.append(table_row)
        
        # Create table
        table = Table(table_data)
        
        # Style the table
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            
            # Alternate row colors for better readability
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Column separators
            ('LINEAFTER', (1, 0), (1, -1), 2, colors.black),
            ('LINEAFTER', (3, 0), (3, -1), 2, colors.black),
            ('LINEAFTER', (5, 0), (5, -1), 2, colors.black),
        ]))
        
        story.append(table)
        
        # Add page break if not the last page
        if page_start + entries_per_page < len(data_list):
            story.append(PageBreak())
    
    # Build the PDF
    doc.build(story)
    print(f"PDF created successfully: {filename}")

# Example usage
# if __name__ == "__main__":
#     # Sample data - replace with your actual data
#     sample_data = [(i, i*10) for i in range(1, 251)]  # 250 entries for demonstration
    
#     # Alternative: if you have your data in a different format, convert it:
#     # your_data = [(1,10), (2,20), (3,30), ...]  # Your actual data here
    
#     create_bundle_pdf(sample_data, "bundle_report.pdf")
    
#     print("Sample data used:")
#     print(f"Total entries: {len(sample_data)}")
#     print(f"First 5 entries: {sample_data[:5]}")
#     print(f"Last 5 entries: {sample_data[-5:]}")


# # Alternative version with more customization options
def create_bundle_pdf_advanced(data_list, filename="bundle_report.pdf", 
                             title="Bundle Report", page_size=A4):
    """
    Advanced version with title and more formatting options.
    """
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    
    doc = SimpleDocTemplate(filename, pagesize=page_size,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    story = []
    
    entries_per_page = 140
    columns = 4
    rows_per_column = entries_per_page // columns
    
    for page_num, page_start in enumerate(range(0, len(data_list), entries_per_page)):
        # Add title for each page
        title_text = f"{title} - Page {page_num + 1}"
        story.append(Paragraph(title_text, styles['Title']))
        story.append(Spacer(1, 0.2*inch))
        
        page_data = data_list[page_start:page_start + entries_per_page]
        
        # Create table as before
        table_data = []
        headers = ['Bundle No', 'Scripts', 'Bundle No', 'Scripts', 
                  'Bundle No', 'Scripts', 'Bundle No', 'Scripts']
        table_data.append(headers)
        
        for row in range(rows_per_column):
            table_row = []
            for col in range(columns):
                index = col * rows_per_column + row
                if index < len(page_data):
                    bundle_no, scripts = page_data[index]
                    table_row.extend([str(bundle_no), str(scripts)])
                else:
                    table_row.extend(['', ''])
            table_data.append(table_row)
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightblue]),
            ('LINEAFTER', (1, 0), (1, -1), 2, colors.navy),
            ('LINEAFTER', (3, 0), (3, -1), 2, colors.navy),
            ('LINEAFTER', (5, 0), (5, -1), 2, colors.navy),
        ]))
        
        story.append(table)
        
        if page_start + entries_per_page < len(data_list):
            story.append(PageBreak())
    
    doc.build(story)
    print(f"Advanced PDF created successfully: {filename}")