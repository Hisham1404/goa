"""
PDF Report Generation Module

This module handles the generation of PDF reports for shapefile comparison results.
It creates comprehensive reports with images, comparison data, and formatted layouts.
"""

import os
import cv2
import tempfile
from typing import List, Dict, Optional, Any

# Import PDF library (with check)
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    print("WARNING: FPDF2 library not found (pip install fpdf2). PDF report generation disabled.")
    FPDF_AVAILABLE = False

# Constants for PDF Layout
PDF_MARGIN = 10
PDF_PAGE_WIDTH = 210 - 2 * PDF_MARGIN  # A4 width (210mm) minus margins
PDF_IMAGE_WIDTH_FULL = PDF_PAGE_WIDTH  # Width for full-width images like the map
PDF_IMAGE_WIDTH_SIDE_BY_SIDE = PDF_PAGE_WIDTH / 2 - 5  # Width for side-by-side images
PDF_THUMBNAIL_WIDTH = PDF_PAGE_WIDTH / 4  # Width for top match thumbnails
PDF_LINE_HEIGHT = 6  # Line height for text


class PDFReport(FPDF):
    """Custom PDF class with header and footer."""
    
    def header(self):
        """Custom header - currently empty."""
        pass

    def footer(self):
        """Custom footer with page number."""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', new_x="LMARGIN", new_y="TOP", align='C')


def create_pdf_report(pdf_filename: str, chosen_index: int,
                     full_map_image_path: Optional[str],
                     reference_image_path: Optional[str],
                     best_match_found: bool, best_match_base_filename: Optional[str],
                     best_match_score_info: str, comparison_method: str,
                     top_results_list: List[Dict[str, Any]], plots_folder: str, 
                     plots_image_extension: str, top_n_matches: int, village_name: str) -> None:
    """
    Generates a PDF report summarizing the comparison findings.
    Includes dynamically sized full map, flipped reference image, and improved layout.
    
    Args:
        pdf_filename: Output PDF file path
        chosen_index: Index of the reference feature
        full_map_image_path: Path to the overview map image
        reference_image_path: Path to the generated reference PNG
        best_match_found: Whether a best match was found
        best_match_base_filename: Base filename of the best match
        best_match_score_info: Score information string
        comparison_method: Method used for comparison ('standard' or 'advanced')
        top_results_list: List of top matching results
        plots_folder: Path to plots folder
        plots_image_extension: File extension for plot images
        top_n_matches: Number of top matches to include
        village_name: Name of the village
    """
    if not FPDF_AVAILABLE:
        print("Cannot generate PDF report because FPDF2 library is not installed.")
        return

    pdf = PDFReport(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Add Full Map Image (Dynamically Scaled)
    _add_map_image(pdf, full_map_image_path)
    
    # Add Title
    _add_title(pdf, chosen_index, comparison_method)
    
    # Add Best Match Overview Section
    _add_best_match_overview(pdf, best_match_found, best_match_base_filename, 
                           best_match_score_info, top_results_list, plots_folder,
                           plots_image_extension, village_name, chosen_index, 
                           reference_image_path)
    
    # Add Top Matches Details Section
    _add_top_matches_details(pdf, top_results_list, top_n_matches, comparison_method,
                           plots_folder, plots_image_extension, village_name)
    
    # Save the PDF
    _save_pdf(pdf, pdf_filename)


def _add_map_image(pdf: PDFReport, full_map_image_path: Optional[str]) -> None:
    """Add the full map image to the PDF with dynamic scaling."""
    if full_map_image_path and os.path.exists(full_map_image_path):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, "Overview Map", new_x="LMARGIN", new_y="NEXT", align='C')
        try:
            # Get original image dimensions using OpenCV
            img = cv2.imread(full_map_image_path)
            if img is None:
                raise ValueError(f"Could not read map image file: {full_map_image_path}")
            orig_h, orig_w = img.shape[:2]
            if orig_w == 0 or orig_h == 0:
                raise ValueError("Map image has zero width or height.")
            aspect_ratio = orig_h / orig_w

            # Determine available space
            avail_w = PDF_PAGE_WIDTH
            max_avail_h = 90  # Max height for the map in mm (adjust as needed)

            # Calculate scaled dimensions preserving aspect ratio
            scaled_h_by_w = avail_w * aspect_ratio  # Height if width is full page width
            scaled_w_by_h = max_avail_h / aspect_ratio  # Width if height is max allowed

            if scaled_h_by_w <= max_avail_h:
                # Fits within height when scaled to full width
                final_w = avail_w
                final_h = scaled_h_by_w
            else:
                # Too tall if scaled to full width, scale to max height instead
                final_h = max_avail_h
                final_w = scaled_w_by_h

            # Center the image horizontally
            x_coord = PDF_MARGIN + (avail_w - final_w) / 2
            x_coord = max(PDF_MARGIN, x_coord)  # Ensure not less than margin

            # Place the image
            current_y_before_map = pdf.get_y()
            pdf.image(full_map_image_path, x=x_coord, y=current_y_before_map, w=final_w, h=final_h)
            pdf.set_y(current_y_before_map + final_h + 2)  # Move below map image + spacing

        except Exception as e:
            print(f"Error processing or adding full map image {full_map_image_path} to PDF: {e}")
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(0, 10, "(Error loading overview map image)", new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.ln(5)
    else:
        if full_map_image_path:  # Only print warning if path was given but file not found
            print(f"Full map image not found or path not provided: {full_map_image_path}")


def _add_title(pdf: PDFReport, chosen_index: int, comparison_method: str) -> None:
    """Add the title section to the PDF."""
    pdf.set_font('Helvetica', 'B', 14)
    pdf.multi_cell(0, 7, f"Comparison Report for Shapefile Feature Index: {chosen_index}", 
                   align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 5, f"Comparison Method Used: {comparison_method.capitalize()}", 
             new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)


def _add_best_match_overview(pdf: PDFReport, best_match_found: bool, 
                           best_match_base_filename: Optional[str],
                           best_match_score_info: str, top_results_list: List[Dict[str, Any]],
                           plots_folder: str, plots_image_extension: str, village_name: str,
                           chosen_index: int, reference_image_path: Optional[str]) -> None:
    """Add the best match overview section with side-by-side images."""
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, "Best Match Overview", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    
    temp_ref_image_path = None  # To store path of temporary flipped image
    
    try:  # Use try...finally to ensure temp file deletion
        if best_match_found and best_match_base_filename:
            # Get the best match sub-village from the top results
            best_match_sub_village = top_results_list[0].get('sub_village', 'unknown') if top_results_list else 'unknown'
            
            best_plot_image_path = _find_plot_image_path(best_match_base_filename, plots_image_extension,
                                                       village_name, best_match_sub_village, plots_folder)
            
            # Store current Y position to align images and text
            start_y_side = pdf.get_y()
            max_image_height = 70  # Max height for these images

            # Add labels for the side-by-side images
            pdf.cell(PDF_PAGE_WIDTH / 2, PDF_LINE_HEIGHT, 
                    f"Reference Feature (Index {chosen_index}, Vertically Flipped)", 
                    new_x="RIGHT", new_y="TOP")
            pdf.set_x(PDF_MARGIN + PDF_PAGE_WIDTH / 2 + 5)
            pdf.cell(PDF_PAGE_WIDTH / 2, PDF_LINE_HEIGHT, 
                    f"Best Matching Plot ({best_match_score_info})", 
                    new_x="LMARGIN", new_y="NEXT")

            image_y = pdf.get_y()
            ref_img_x = PDF_MARGIN

            # Load, Flip, Save Temp, and Draw Reference Image (Left)
            temp_ref_image_path = _add_flipped_reference_image(pdf, reference_image_path, 
                                                             ref_img_x, image_y, max_image_height)
            
            # Draw Best Match Plot Image (Right)
            plot_img_x = PDF_MARGIN + PDF_PAGE_WIDTH / 2 + 5
            _add_plot_image(pdf, best_plot_image_path, plot_img_x, image_y, max_image_height)

            pdf.set_y(image_y + max_image_height + 5)  # Move below the images

        else:
            pdf.cell(0, 10, "No best match found during comparison.", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)  # Reduced spacing

    finally:
        # Cleanup Temporary Flipped Reference Image
        if temp_ref_image_path and os.path.exists(temp_ref_image_path):
            try:
                os.remove(temp_ref_image_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_ref_image_path}: {e}")


def _find_plot_image_path(best_match_base_filename: str, plots_image_extension: str,
                         village_name: str, best_match_sub_village: str, 
                         plots_folder: str) -> Optional[str]:
    """Find the path to the best match plot image using sophisticated search logic."""
    best_plot_image_path = None
    
    # Try multiple extensions
    extensions_to_try = ['.png', '.jpg', '.jpeg', plots_image_extension]
    # Remove duplicates while preserving order
    extensions_to_try = list(dict.fromkeys(extensions_to_try))
    
    # First try the specific sub-village folder
    for extension in extensions_to_try:
        potential_plots_paths = [
            os.path.join("maps", village_name, "plots", best_match_sub_village, "contours", f"{best_match_base_filename}{extension}"),
            os.path.join("maps", village_name, "plots", best_match_sub_village, "contour", f"{best_match_base_filename}{extension}"),
            os.path.join("maps", village_name, "plots", best_match_sub_village, f"{best_match_base_filename}{extension}"),
            os.path.join("maps", village_name, "plots", best_match_sub_village, "enhanced", f"{best_match_base_filename}{extension}")
        ]
        
        for potential_path in potential_plots_paths:
            if os.path.exists(potential_path):
                best_plot_image_path = potential_path
                break
        
        if best_plot_image_path:
            break
    
    # Fallback: try the plots_folder parameter if provided (for backwards compatibility)
    if best_plot_image_path is None:
        for extension in extensions_to_try:
            potential_plots_paths = [
                os.path.join(plots_folder, "contours", f"{best_match_base_filename}{extension}"),
                os.path.join(plots_folder, "contour", f"{best_match_base_filename}{extension}"),
                os.path.join(plots_folder, f"{best_match_base_filename}{extension}"),
                os.path.join(plots_folder, "enhanced", f"{best_match_base_filename}{extension}")
            ]
            
            for potential_path in potential_plots_paths:
                if os.path.exists(potential_path):
                    best_plot_image_path = potential_path
                    break
            
            if best_plot_image_path:
                break
    
    return best_plot_image_path


def _add_flipped_reference_image(pdf: PDFReport, reference_image_path: Optional[str],
                               ref_img_x: float, image_y: float, max_image_height: float) -> Optional[str]:
    """Add the flipped reference image to the PDF and return the temp file path."""
    temp_ref_image_path = None
    
    if reference_image_path and os.path.exists(reference_image_path):
        try:
            ref_image = cv2.imread(reference_image_path)
            if ref_image is not None:
                flipped_ref_image = cv2.flip(ref_image, 0)
                # Create a named temporary file for the flipped image
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_f:
                    temp_ref_image_path = temp_f.name
                if cv2.imwrite(temp_ref_image_path, flipped_ref_image):
                    pdf.image(temp_ref_image_path, x=ref_img_x, y=image_y, 
                             w=PDF_IMAGE_WIDTH_SIDE_BY_SIDE, h=max_image_height)
                else:
                    raise IOError("Failed to write temporary flipped image.")
            else:
                raise ValueError("Reference image loaded as None.")
        except Exception as e:
            print(f"Error processing/flipping reference image for PDF: {e}")
            pdf.set_xy(ref_img_x + 5, image_y + 5)
            pdf.multi_cell(PDF_IMAGE_WIDTH_SIDE_BY_SIDE - 10, PDF_LINE_HEIGHT, 
                          "(Error Loading/Flipping Ref Img)", border=1, align='C')
            pdf.set_y(image_y)  # Reset Y position after error text
    else:
        pdf.set_xy(ref_img_x + 5, image_y + 5)
        pdf.multi_cell(PDF_IMAGE_WIDTH_SIDE_BY_SIDE - 10, PDF_LINE_HEIGHT, 
                      "(Reference Image Not Available)", border=1, align='C')
        pdf.set_y(image_y)
    
    return temp_ref_image_path


def _add_plot_image(pdf: PDFReport, best_plot_image_path: Optional[str],
                   plot_img_x: float, image_y: float, max_image_height: float) -> None:
    """Add the best match plot image to the PDF."""
    pdf.set_x(plot_img_x)
    try:
        if best_plot_image_path and os.path.exists(best_plot_image_path):
            pdf.image(best_plot_image_path, x=plot_img_x, y=image_y, 
                     w=PDF_IMAGE_WIDTH_SIDE_BY_SIDE, h=max_image_height)
        else:
            error_msg = f"(Plot Image Not Found:\n{os.path.basename(best_plot_image_path) if best_plot_image_path else 'Path is None'})"
            pdf.set_xy(plot_img_x + 5, image_y + 5)
            pdf.multi_cell(PDF_IMAGE_WIDTH_SIDE_BY_SIDE - 10, PDF_LINE_HEIGHT, 
                          error_msg, border=1, align='C')
            pdf.set_y(image_y)
    except Exception as e:
        print(f"Error adding best match plot image to PDF: {e}")
        pdf.set_xy(plot_img_x + 5, image_y + 5)
        pdf.multi_cell(PDF_IMAGE_WIDTH_SIDE_BY_SIDE - 10, PDF_LINE_HEIGHT, 
                      "(Error Loading Plot Img)", border=1, align='C')
        pdf.set_y(image_y)


def _add_top_matches_details(pdf: PDFReport, top_results_list: List[Dict[str, Any]], 
                           top_n_matches: int, comparison_method: str,
                           plots_folder: str, plots_image_extension: str, 
                           village_name: str) -> None:
    """Add the top matches details section with thumbnails and data."""
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f"Top {min(top_n_matches, len(top_results_list))} Match Details", 
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 9)

    if not top_results_list:
        pdf.cell(0, 10, "No comparison results available.", new_x="LMARGIN", new_y="NEXT")
        return

    page_height = pdf.h - pdf.t_margin - pdf.b_margin  # Printable height
    max_thumb_h = 30  # Height for thumbnails
    # Estimate required height per item (thumbnail + ~4 lines text + spacing)
    estimated_item_height = max_thumb_h + (4 * PDF_LINE_HEIGHT / 1.5) + 6  # Approx height needed

    for i, res in enumerate(top_results_list[:top_n_matches]):
        # Check if we need a new page BEFORE adding the item
        current_y_before_item = pdf.get_y()
        # Add a buffer (e.g., 5mm) to avoid placing exactly at the bottom margin
        if current_y_before_item + estimated_item_height > page_height - 5:
            pdf.add_page()
            # Optional: Re-add section header on new page
            pdf.set_font('Helvetica', 'I', 10)
            pdf.cell(0, 6, "... Top Match Details (continued) ...", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 9)  # Reset font after page break
            current_y_before_item = pdf.get_y()  # Update Y after potentially adding a page

        # Determine base filename and construct plot image path
        source_identifier = res.get('filename', res.get('img_path', ''))
        if not source_identifier:
            continue
        match_base_filename = os.path.splitext(os.path.basename(source_identifier))[0]
        
        # Get the sub-village for this specific result
        result_sub_village = res.get('sub_village', '')
        
        # Use sophisticated search logic like in the visualization function
        match_plot_image_path = _find_match_plot_image_path(match_base_filename, 
                                                           plots_image_extension,
                                                           village_name, result_sub_village, 
                                                           plots_folder)

        start_y_item = pdf.get_y()  # Y position for this specific item
        thumbnail_x = PDF_MARGIN
        text_x = thumbnail_x + PDF_THUMBNAIL_WIDTH + 5
        text_width = PDF_PAGE_WIDTH - PDF_THUMBNAIL_WIDTH - 10

        # Draw Thumbnail Image
        _add_thumbnail_image(pdf, match_plot_image_path, thumbnail_x, start_y_item, max_thumb_h)

        # Add Text Details
        _add_match_text_details(pdf, text_x, start_y_item, text_width, i, match_base_filename,
                              plots_image_extension, comparison_method, res)

        # Ensure we move below the potentially taller block (image or text) for the next item
        text_end_y = pdf.get_y()  # Get Y position after writing text
        image_end_y = start_y_item + max_thumb_h + 2  # Y position below image
        pdf.set_y(max(image_end_y, text_end_y))  # Move below the taller element


def _find_match_plot_image_path(match_base_filename: str, plots_image_extension: str,
                               village_name: str, result_sub_village: str, 
                               plots_folder: str) -> Optional[str]:
    """Find the path to a match plot image."""
    match_plot_image_path = None
    
    if result_sub_village:
        # Try multiple extensions including .png
        for extension in ['.png', '.jpg', '.jpeg']:
            potential_paths = [
                os.path.join("maps", village_name, "plots", result_sub_village, "contours", f"{match_base_filename}{extension}"),
                os.path.join("maps", village_name, "plots", result_sub_village, "contour", f"{match_base_filename}{extension}"),
                os.path.join("maps", village_name, "plots", result_sub_village, f"{match_base_filename}{extension}"),
                os.path.join("maps", village_name, "plots", result_sub_village, "enhanced", f"{match_base_filename}{extension}")
            ]
            
            for potential_path in potential_paths:
                if os.path.exists(potential_path):
                    match_plot_image_path = potential_path
                    break
            
            if match_plot_image_path:
                break
    
    # Fallback to simple plots_folder path if not found or no sub_village info
    if match_plot_image_path is None:
        # Try multiple extensions for fallback
        for extension in ['.png', '.jpg', '.jpeg']:
            fallback_path = os.path.join(plots_folder, f"{match_base_filename}{extension}")
            if os.path.exists(fallback_path):
                match_plot_image_path = fallback_path
                break
        
        # Final fallback using the configured extension
        if match_plot_image_path is None:
            match_plot_image_path = os.path.join(plots_folder, f"{match_base_filename}{plots_image_extension}")
    
    return match_plot_image_path


def _add_thumbnail_image(pdf: PDFReport, match_plot_image_path: Optional[str],
                        thumbnail_x: float, start_y_item: float, max_thumb_h: float) -> None:
    """Add a thumbnail image to the PDF."""
    try:
        if match_plot_image_path and os.path.exists(match_plot_image_path):
            pdf.image(match_plot_image_path, x=thumbnail_x, y=start_y_item, 
                     w=PDF_THUMBNAIL_WIDTH, h=max_thumb_h)
        else:
            pdf.set_xy(thumbnail_x + 2, start_y_item + 2)
            pdf.cell(PDF_THUMBNAIL_WIDTH - 4, max_thumb_h - 4, "(Plot Img Missing)", 
                    border=1, align='C')
            pdf.set_y(start_y_item)  # Reset Y in this column
    except Exception as e:
        print(f"Error adding thumbnail {match_plot_image_path} to PDF: {e}")
        pdf.set_xy(thumbnail_x + 2, start_y_item + 2)
        pdf.cell(PDF_THUMBNAIL_WIDTH - 4, max_thumb_h - 4, "(Img Error)", 
                border=1, align='C')
        pdf.set_y(start_y_item)


def _add_match_text_details(pdf: PDFReport, text_x: float, start_y_item: float, 
                          text_width: float, i: int, match_base_filename: str,
                          plots_image_extension: str, comparison_method: str, 
                          res: Dict[str, Any]) -> None:
    """Add text details for a match result."""
    pdf.set_xy(text_x, start_y_item)
    pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                   f"{i+1}. Plot: {match_base_filename}{plots_image_extension}")
    
    if comparison_method == 'standard':
        iou_note = " (Prioritized)" if res.get('iou_transform') == "Flipped Vertically" else ""
        haus_note = " (Prioritized)" if res.get('hausdorff_transform') == "Flipped Vertically" else ""
        haus_dist_str = f"{res.get('hausdorff', float('inf')):.2f}" if res.get('hausdorff', float('inf')) != float('inf') else "Inf/Error"
        
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   IoU: {res.get('iou', 0.0):.4f} (T: {res.get('iou_transform', 'N/A')}{iou_note})")
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   Hausdorff: {haus_dist_str} (T: {res.get('hausdorff_transform', 'N/A')}{haus_note})")
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   Source DAT: {res.get('filename', 'N/A')}")
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   Sub-village: {res.get('sub_village', 'N/A')}")

    elif comparison_method == 'advanced':
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   VGG Similarity: {res.get('similarity', 0.0):.4f}")
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   Source Image: {os.path.basename(res.get('img_path', 'N/A'))}")
        pdf.set_x(text_x)
        pdf.multi_cell(text_width, PDF_LINE_HEIGHT / 1.5, 
                      f"   Sub-village: {res.get('sub_village', 'N/A')}")


def _save_pdf(pdf: PDFReport, pdf_filename: str) -> None:
    """Save the PDF report to file."""
    try:
        pdf.output(pdf_filename)
        print(f"\nPDF report generated successfully: {pdf_filename}")
    except Exception as e:
        print(f"\nError saving PDF report {pdf_filename}: {e}")


def is_pdf_generation_available() -> bool:
    """Check if PDF generation is available (FPDF2 installed)."""
    return FPDF_AVAILABLE
