#!/usr/bin/env python3
"""
Convert XML files to Markdown format.
Handles the specific XML structure used in this project.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def clean_text(text):
    """Clean and normalize text content."""
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def xml_to_markdown(element, level=0, last_was_block=False):
    """Recursively convert XML element to Markdown."""
    markdown = []
    prev_was_block = last_was_block
    
    # Get text before first child
    if element.text:
        text = clean_text(element.text)
        if text:
            markdown.append(text)
    
    # Process children
    for child in element:
        tag = child.tag
        is_block_element = tag in ['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol']
        
        if tag == 'h1':
            content = ''.join(child.itertext())
            markdown.append(f"\n# {clean_text(content)}\n")
            prev_was_block = True
        elif tag == 'h2':
            content = ''.join(child.itertext())
            markdown.append(f"\n## {clean_text(content)}\n")
            prev_was_block = True
        elif tag == 'h3':
            content = ''.join(child.itertext())
            markdown.append(f"\n### {clean_text(content)}\n")
            prev_was_block = True
        elif tag == 'h4':
            content = ''.join(child.itertext())
            markdown.append(f"\n#### {clean_text(content)}\n")
            prev_was_block = True
        elif tag == 'p':
            # Extract all text from paragraph and its children
            content = extract_paragraph_content(child)
            if content:
                # Paragraphs in Markdown need blank lines between them
                markdown.append(f"{content}\n\n")
                prev_was_block = True
        elif tag == 'ul':
            list_items = []
            for li in child.findall('li'):
                li_content = extract_paragraph_content(li)
                if li_content:
                    list_items.append(f"- {li_content}")
            if list_items:
                # Join items with single newline (no blank lines between items)
                list_text = "\n".join(list_items)
                # Add blank line before list if previous was a block element
                prefix = "\n" if prev_was_block else ""
                # Add blank line after list (will be followed by something else)
                markdown.append(f"{prefix}{list_text}\n\n")
                prev_was_block = True
        elif tag == 'ol':
            list_items = []
            for idx, li in enumerate(child.findall('li'), 1):
                li_content = extract_paragraph_content(li)
                if li_content:
                    list_items.append(f"{idx}. {li_content}")
            if list_items:
                # Join items with single newline (no blank lines between items)
                list_text = "\n".join(list_items)
                # Add blank line before list if previous was a block element
                prefix = "\n" if prev_was_block else ""
                # Add blank line after list (will be followed by something else)
                markdown.append(f"{prefix}{list_text}\n\n")
                prev_was_block = True
        elif tag in ['div', 'Story', 'Body', 'Root']:
            # Container elements - just process children
            child_md = xml_to_markdown(child, level, prev_was_block)
            markdown.append(child_md)
            # Update prev_was_block based on last element in child
            if child_md.strip():
                prev_was_block = True
        elif tag == 'span':
            # Span tags - just get the text content
            content = ''.join(child.itertext())
            markdown.append(clean_text(content))
            prev_was_block = False
        else:
            # Unknown tag - try to extract text
            content = ''.join(child.itertext())
            if content:
                markdown.append(clean_text(content))
            prev_was_block = False
        
        # Get text after child
        if child.tail:
            tail = clean_text(child.tail)
            if tail:
                markdown.append(tail)
                prev_was_block = False
    
    return ''.join(markdown)


def extract_paragraph_content(element):
    """Extract formatted content from a paragraph element."""
    parts = []
    
    if element.text:
        text = element.text
        # Preserve tabs for item formatting
        if '\t' in text:
            parts.append(text)
        else:
            parts.append(clean_text(text))
    
    for child in element:
        tag = child.tag
        content = ''.join(child.itertext())
        
        if tag == 'em':
            parts.append(f"*{clean_text(content)}*")
        elif tag == 'strong':
            parts.append(f"**{clean_text(content)}**")
        elif tag == 'span':
            # For tags in spans, preserve formatting
            parts.append(clean_text(content))
        else:
            parts.append(clean_text(content))
        
        if child.tail:
            tail = child.tail
            # Preserve tabs
            if '\t' in tail:
                parts.append(tail)
            else:
                tail_clean = clean_text(tail)
                if tail_clean:
                    parts.append(tail_clean)
    
    result = ''.join(parts)
    # Clean up but preserve tabs
    if '\t' not in result:
        result = clean_text(result)
    return result


def convert_xml_file(xml_path, output_path):
    """Convert a single XML file to Markdown."""
    try:
        # Read file and fix common XML issues
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix unescaped ampersands (but not already escaped ones or part of entities)
        # Match & that are not followed by valid entity characters
        def fix_ampersand(match):
            text = match.group(0)
            # If it's already a valid entity, leave it
            if re.match(r'&[a-zA-Z]+;', text):
                return text
            # If it's part of a common pattern like R&R, escape it
            if 'R&R' in text:
                return text.replace('R&R', 'R&amp;R')
            # Otherwise escape standalone &
            return text.replace('&', '&amp;')
        
        # Fix ampersands in text content (not in tags)
        lines = content.split('\n')
        fixed_lines = []
        for line in lines:
            # Only fix & in text content, not in tag attributes
            if '&' in line and not re.search(r'<[^>]*&[^>]*>', line):
                # Fix R&R pattern
                line = line.replace('R&R', 'R&amp;R')
                # Fix other standalone & (but be careful with entities)
                line = re.sub(r'&(?![a-zA-Z]{2,};)', '&amp;', line)
            fixed_lines.append(line)
        content = '\n'.join(fixed_lines)
        
        # Try to fix mismatched div tags in Field_Medic.xml
        if 'Field_Medic.xml' in str(xml_path):
            # The issue is line 71 has a closing div without proper structure
            # Let's wrap the orphan paragraph in a div
            content = content.replace(
                '</ul></div>\n<p>I am working on teaching',
                '</ul>\n<p>I am working on teaching'
            )
        
        # Parse XML
        root = ET.fromstring(content)
        
        # Convert to markdown
        markdown = xml_to_markdown(root)
        
        # Clean up extra newlines but preserve paragraph spacing
        # Headings should have a blank line after them
        markdown = re.sub(r'(#+\s+[^\n]+)\n([^\n#])', r'\1\n\n\2', markdown)
        # Ensure list items don't have blank lines between them
        # But keep blank line after the list ends
        markdown = re.sub(r'(-|\d+\.\s+[^\n]+)\n\n(-|\d+\.)', r'\1\n\2', markdown)
        # Clean up excessive newlines (4+ becomes 2)
        markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)
        # Clean up triple newlines to double (but keep double for paragraphs)
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        markdown = markdown.strip() + '\n'
        
        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"Converted: {xml_path} -> {output_path}")
        return True
    except Exception as e:
        print(f"Error converting {xml_path}: {e}")
        return False


def main():
    """Convert all XML files in the text directory to Markdown."""
    base_dir = Path("/Users/oli/Documents/GitHub/Deathworld")
    text_dir = base_dir / "text"
    
    # Find all XML files
    xml_files = list(text_dir.rglob("*.xml"))
    
    if not xml_files:
        print("No XML files found in text directory")
        return
    
    print(f"Found {len(xml_files)} XML files to convert")
    
    converted = 0
    for xml_path in xml_files:
        # Create output path (same location, .md extension)
        relative_path = xml_path.relative_to(text_dir)
        output_path = text_dir / relative_path.with_suffix('.md')
        
        if convert_xml_file(xml_path, output_path):
            converted += 1
    
    print(f"\nConversion complete: {converted}/{len(xml_files)} files converted")


if __name__ == "__main__":
    main()
