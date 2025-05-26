import pytest
from hyperlint.utils import MDXParser


class TestMDXParser:
    def test_basic_mdx_parsing(self):
        """Test basic MDX parsing with JSX components."""
        content = """# Title

import { Button } from './Button'

Normal markdown paragraph.

<Button onClick={() => console.log('test')}>
  Click me
</Button>

Another paragraph.

export default Button
"""
        parser = MDXParser(content)
        
        # Import statement should be protected
        assert parser.is_protected_line(3)
        
        # Normal markdown should not be protected
        assert not parser.is_protected_line(5)
        
        # JSX component should be protected
        assert parser.is_protected_line(7)
        assert parser.is_protected_line(8)
        assert parser.is_protected_line(9)
        
        # Normal markdown after component should not be protected
        assert not parser.is_protected_line(11)
        
        # Export statement should be protected
        assert parser.is_protected_line(13)

    def test_self_closing_jsx_components(self):
        """Test self-closing JSX components."""
        content = """# Title

<CustomComponent prop="value" />

Normal text."""
        
        parser = MDXParser(content)
        
        # Self-closing component should be protected
        assert parser.is_protected_line(3)
        
        # Normal text should not be protected
        assert not parser.is_protected_line(5)

    def test_jsx_expressions(self):
        """Test JSX expressions in curly braces."""
        content = """# Title

Some text with {variable} expression.

<Component prop={someValue}>
  Content with {anotherVariable} here
</Component>

Regular text."""
        
        parser = MDXParser(content)
        
        # Line with JSX expression should be protected
        assert parser.is_protected_line(3)
        
        # Component lines should be protected
        assert parser.is_protected_line(5)
        assert parser.is_protected_line(6)
        assert parser.is_protected_line(7)
        
        # Regular text should not be protected
        assert not parser.is_protected_line(9)

    def test_nested_jsx_components(self):
        """Test nested JSX components."""
        content = """<OuterComponent>
  <InnerComponent prop="value">
    <DeepComponent />
  </InnerComponent>
</OuterComponent>"""
        
        parser = MDXParser(content)
        
        # All lines should be protected
        for line_num in range(1, 6):
            assert parser.is_protected_line(line_num)

    def test_mixed_content(self):
        """Test mixed MDX and markdown content."""
        content = """# Heading

Regular paragraph.

import React from 'react'

<Component>
  JSX content
</Component>

Another paragraph.

{/* JSX comment */}

Final paragraph.

export { Component }"""
        
        parser = MDXParser(content)
        
        # Regular markdown should not be protected
        assert not parser.is_protected_line(1)  # Heading
        assert not parser.is_protected_line(3)  # Regular paragraph
        assert not parser.is_protected_line(11) # Another paragraph
        assert not parser.is_protected_line(15) # Final paragraph
        
        # Import/export should be protected
        assert parser.is_protected_line(5)   # import
        assert parser.is_protected_line(17)  # export
        
        # JSX component should be protected
        assert parser.is_protected_line(7)   # <Component>
        assert parser.is_protected_line(8)   # JSX content
        assert parser.is_protected_line(9)   # </Component>
        
        # JSX comment should be protected
        assert parser.is_protected_line(13)  # {/* JSX comment */}

    def test_get_protected_regions(self):
        """Test getting protected regions."""
        content = """# Title

import { Button } from './Button'

<Button>Click</Button>

Normal text.

export default Button"""
        
        parser = MDXParser(content)
        regions = parser.get_protected_regions()
        
        # Should have 3 protected regions: import, component, export
        assert len(regions) == 3
        assert (3, 3) in regions  # import line
        assert (5, 5) in regions  # button component
        assert (9, 9) in regions  # export line

    def test_empty_content(self):
        """Test parser with empty content."""
        parser = MDXParser("")
        assert parser.get_protected_regions() == []
        assert not parser.is_protected_line(1)

    def test_markdown_only_content(self):
        """Test parser with markdown-only content."""
        content = """# Title

This is a regular markdown file.

## Subtitle

- List item 1
- List item 2

Regular paragraph."""
        
        parser = MDXParser(content)
        
        # No lines should be protected in pure markdown
        for line_num in range(1, 10):
            assert not parser.is_protected_line(line_num)
        
        assert parser.get_protected_regions() == []