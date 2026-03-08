import { useState } from "react";
import BookSelector from "./features/book-selector/BookSelector";
import ChatPanel from "./features/chat/ChatPanel";
import PdfViewer from "./features/pdf-viewer/PdfViewer";
import ResizeHandle from "./components/ResizeHandle";
import { AppProvider } from "./context/AppContext";

export default function App() {
  const [leftWidth, setLeftWidth] = useState(
    () => Math.round(window.innerWidth / 2),
  );

  return (
    <AppProvider>
      <div className="flex h-screen flex-col">
        {/* Header */}
        <header className="flex items-center gap-4 border-b bg-white px-4 py-2">
          <h1 className="text-lg font-bold text-gray-800 shrink-0">
            📚 Textbook RAG
          </h1>
          <div className="w-80">
            <BookSelector />
          </div>
        </header>

        {/* Two-column layout */}
        <div className="flex flex-1 min-h-0">
          {/* Left: PDF Viewer */}
          <div className="h-full overflow-hidden" style={{ width: leftWidth }}>
            <PdfViewer />
          </div>
          <ResizeHandle width={leftWidth} onResize={setLeftWidth} min={300} max={1400} />
          {/* Right: Chat */}
          <div className="flex-1 h-full overflow-hidden min-w-[300px]">
            <ChatPanel />
          </div>
        </div>
      </div>
    </AppProvider>
  );
}
