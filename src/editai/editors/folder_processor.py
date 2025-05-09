from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Union
import os

from loguru import logger
from pydantic import BaseModel, Field, FilePath, DirectoryPath

from .core import BaseEditor
from ..utils import find_markdown_files


class FolderProcessor(BaseModel):
    """
    Process multiple markdown files in a directory using a specified editor.
    
    This class acts as a wrapper around the editor classes, applying them to 
    multiple files in a directory rather than a single file.
    """
    
    directory_path: DirectoryPath
    editor_class: Type[BaseEditor]
    editor_kwargs: Dict[str, Any] = Field(default_factory=dict)
    include_pattern: str = "*.md"
    exclude_patterns: List[str] = Field(default_factory=list)
    recursive: bool = True
    
    def process_directory(self, dry_run: bool = False) -> Dict[Path, str]:
        """
        Process all markdown files in the directory using the specified editor.
        
        Args:
            dry_run: If True, don't modify the files, just return what would be changed.
            
        Returns:
            A dictionary mapping file paths to their processed content.
        """
        # Find all markdown files in the directory
        search_pattern = f"**/{self.include_pattern}" if self.recursive else self.include_pattern
        file_paths = list(self.directory_path.glob(search_pattern))
        
        if not file_paths:
            logger.warning(f"No files found matching pattern '{self.include_pattern}' in {self.directory_path}")
            return {}
        
        # Apply exclude patterns if any
        if self.exclude_patterns:
            excluded_files = set()
            for pattern in self.exclude_patterns:
                pattern_with_recursion = f"**/{pattern}" if self.recursive else pattern
                excluded_files.update(self.directory_path.glob(pattern_with_recursion))
            
            file_paths = [f for f in file_paths if f not in excluded_files]
        
        logger.info(f"Found {len(file_paths)} files to process in {self.directory_path}")
        
        # Process each file
        results = {}
        for file_path in file_paths:
            try:
                # Create editor instance for this file
                editor = self.editor_class(path=file_path, **self.editor_kwargs)
                
                # Run prerun checks
                if not editor.prerun_checks():
                    logger.warning(f"Prerun checks failed for {file_path}, skipping")
                    continue
                
                # Process the file
                processed_content = editor.generate_v2()
                results[file_path] = processed_content
                
                # Write the processed content back to the file if not in dry run mode
                if not dry_run:
                    relative_path = file_path.relative_to(self.directory_path)
                    logger.info(f"Writing changes to {relative_path}")
                    with open(file_path, 'w') as f:
                        f.write(processed_content)
                else:
                    logger.info(f"Dry run - would update {file_path.relative_to(self.directory_path)}")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
        
        return results
    
    def process_file(self, file_path: Path) -> Optional[str]:
        """
        Process a single file using the specified editor.
        
        Args:
            file_path: The path to the file to process.
            
        Returns:
            The processed content of the file, or None if processing failed.
        """
        try:
            # Create editor instance for this file
            editor = self.editor_class(path=file_path, **self.editor_kwargs)
            
            # Run prerun checks
            if not editor.prerun_checks():
                logger.warning(f"Prerun checks failed for {file_path}, skipping")
                return None
            
            # Process the file
            return editor.generate_v2()
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return None