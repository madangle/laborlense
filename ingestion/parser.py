import fitz  # pymupdf
import re
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class ParsedChunk:
    """A single chunk of text from a legal document"""
    content: str
    article_number: str = ""
    section: str = ""
    hierarchy_path: str = ""
    page_number: int = 0
    has_table: bool = False
    cross_references: List[str] = field(default_factory=list)


def extract_cross_references(text: str) -> List[str]:
    """Find all article references within text e.g. 'Article 43', 'Article (12)'"""
    pattern = r'[Aa]rticle\s+\(?(\d+)\)?'
    matches = re.findall(pattern, text)
    return [f"Article {m}" for m in set(matches)]


def detect_article_number(text: str) -> str:
    """Extract article number from the start of a chunk"""
    # Matches: "Article 1", "Article (1)", "ARTICLE 1"
    match = re.match(r'^[Aa]rticle\s+\(?(\d+)\)?', text.strip())
    if match:
        return f"Article {match.group(1)}"
    return ""


def detect_section(text: str) -> str:
    """Extract chapter/section heading"""
    # Matches: "Chapter One", "Chapter 1", "CHAPTER 1", "Part II"
    match = re.match(r'^(Chapter|CHAPTER|Part|PART|Section|SECTION)\s+\S+', text.strip())
    if match:
        return match.group(0).title()
    return ""


def parse_legal_pdf(filepath: str, document_title: str) -> List[ParsedChunk]:
    """
    Parse a legal PDF into article-level chunks.
    
    Key decision: we chunk by Article, not by token count.
    This preserves the legal structure and makes citations accurate.
    """
    doc = fitz.open(filepath)
    chunks = []
    
    current_article = ""
    current_section = ""
    current_content = []
    current_page = 1
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect new section heading
            section = detect_section(line)
            if section:
                current_section = section
                continue
            
            # Detect new article — this triggers saving the previous chunk
            article = detect_article_number(line)
            if article:
                # Save the previous article as a chunk
                if current_content and current_article:
                    content = '\n'.join(current_content).strip()
                    if len(content) > 50:  # skip tiny fragments
                        chunks.append(ParsedChunk(
                            content=content,
                            article_number=current_article,
                            section=current_section,
                            hierarchy_path=f"{current_section} > {current_article}",
                            page_number=current_page,
                            has_table=False,
                            cross_references=extract_cross_references(content)
                        ))
                
                # Start new article
                current_article = article
                current_content = [line]
                current_page = page_num
            
            elif current_article:
                current_content.append(line)
    
    # Don't forget the last article
    if current_content and current_article:
        content = '\n'.join(current_content).strip()
        if len(content) > 50:
            chunks.append(ParsedChunk(
                content=content,
                article_number=current_article,
                section=current_section,
                hierarchy_path=f"{current_section} > {current_article}",
                page_number=current_page,
                has_table=False,
                cross_references=extract_cross_references(content)
            ))
    
    print(f"✅ Parsed {len(chunks)} chunks from {document_title}")
    return chunks


if __name__ == "__main__":
    # Quick test
    chunks = parse_legal_pdf(
        "./documents/federal_decree_law_33_2021.pdf",
        "Federal Decree-Law No. 33 of 2021"
    )
    
    print(f"\nFirst 3 chunks:")
    for chunk in chunks[:3]:
        print(f"\n{'='*50}")
        print(f"Article: {chunk.article_number}")
        print(f"Section: {chunk.section}")
        print(f"Path: {chunk.hierarchy_path}")
        print(f"Cross-refs: {chunk.cross_references}")
        print(f"Content preview: {chunk.content[:200]}...")