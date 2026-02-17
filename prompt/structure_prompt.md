# C Project Directory Context

## Overview

Below is a string representation of a C project directory. Use this as your
reference for understanding the project's structure, locating files, and
reading file contents. All file paths are relative to the project root.

---

## How to Use This Reference

- **Finding files:** Use the directory tree to locate files by path.
- **Reading contents:** File contents are included beneath each file entry.
- **Understanding structure:** The tree reflects the actual layout of the
  project on disk, including all source files, headers, build files, and
  configuration.
- **Making edits:** When proposing changes to a file, always reference it
  by its full relative path as shown in the tree.

---

## Directory Tree

```
{structure}
```

*This is a hierarchical representation of all files and folders in the
project, starting from the project root.*

---

## Notes

- Binary files (e.g. compiled `.o` objects, executables) are listed in the
  tree but their contents are not included.
- Auto-generated files (e.g. `CMakeCache.txt`, `compile_commands.json`) are
  included for reference but should not be manually edited.
- If a file is listed in the tree but has no content block below, it was
  either empty or excluded from this snapshot.