"""Insert ?books= handler into ChatPage.tsx"""
import pathlib

file = pathlib.Path(r"c:\Users\40270\Desktop\workspace\textbook-rag\payload-v2\src\features\chat\ChatPage.tsx")
content = file.read_text(encoding="utf-8")

insert_code = '''

  /**
   * Handle ?books=id1,id2,id3 — start a scoped session with specific books.
   * Used by Files tab "New Chat" action to scope chat to selected documents.
   */
  useEffect(() => {
    const booksParam = searchParams.get('books')
    if (!booksParam) return
    const ids = booksParam.split(',').map(Number).filter((n) => !isNaN(n) && n > 0)
    if (ids.length === 0) return
    setActiveSessionId(null)
    setPdfTabs([])
    setActiveTabBookId(null)
    dispatch({ type: 'START_SESSION', bookIds: ids })
    router.replace('/chat')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])
'''

# Find the anchor: the second "}, [searchParams])" before "Auto-open / switch PDF tab"
anchor = "  }, [searchParams])\r\n\r\n  /**\r\n   * Auto-open / switch PDF tab"
if anchor not in content:
    # Try LF
    anchor = "  }, [searchParams])\n\n  /**\n   * Auto-open / switch PDF tab"

if anchor in content:
    replacement = "  }, [searchParams])" + insert_code + "\n\n  /**\n   * Auto-open / switch PDF tab"
    content = content.replace(anchor, replacement, 1)
    file.write_text(content, encoding="utf-8")
    print("SUCCESS: Inserted ?books= handler")
else:
    print("ERROR: Anchor not found")
    # Show a snippet around the area
    idx = content.find("Auto-open")
    if idx >= 0:
        print(f"Found 'Auto-open' at char {idx}")
        print(repr(content[max(0,idx-100):idx+50]))
