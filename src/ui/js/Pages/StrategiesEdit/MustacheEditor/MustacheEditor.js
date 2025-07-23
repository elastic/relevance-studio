// /Users/lilyadler/relevance-studio/src/ui/js/Components/MustacheEditor/MustacheEditor.js
import React, { useEffect, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import './MustacheEditor.css';

const MustacheEditor = ({ value, onChange, darkMode, ...props }) => {
  const editorRef = useRef(null);
  const [decorations, setDecorations] = useState([]);

  // Called once on mount, and whenever content changes
  const handleMount = (editor) => {
    editorRef.current = editor;
    // Highlight initial tokens
    updateDecorations(editor);

    // Re‑highlight on every edit
    editor.onDidChangeModelContent(() => {
      updateDecorations(editor);
    });
  };

  function updateDecorations(editor) {
    const model = editor.getModel();
    if (!model) return;

    // Find all occurrences of {{…}}
    const matches = model.findMatches(
      '{{[^}]*}}',
      true,  // searchInComments
      true,  // isRegex
      false, // matchCase
      null,  // wordSep
      false  // captureGrp
    );

    // Map matches → decorations
    const newDecs = matches.map(m => ({
      range: m.range,
      options: { inlineClassName: 'mustache-token' }
    }));

    // Apply them, keep track so we can clear next time
    const applied = editor.deltaDecorations(decorations, newDecs);
    setDecorations(applied);
  }

  return (
    <Editor
      height="100%"
      language="json"
      value={value}
      onChange={onChange}
      onMount={handleMount}
      theme={darkMode ? 'vs-dark' : 'vs-light'}
      options={{
        minimap: { enabled: false },
        fontSize: 12,
        folding: true,
        tabSize: 2,
        ...props.options
      }}
      {...props}
    />
  );
};

export default MustacheEditor;