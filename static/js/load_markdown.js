document.addEventListener("DOMContentLoaded", () => {
  const textAreasSelector = "div > textarea"
  const textAreas = document.querySelectorAll(textAreasSelector)

  setTimeout(() => {
    textAreas.forEach((textArea) => {
      new SimpleMDE({
        element: textArea,
        toolbar: [
          "bold",
          "italic",
          "heading",
          "|",
          "quote",
          "code",
          "link",
          "image",
          "|",
          "unordered-list",
          "ordered-list",
          "|",
          "undo",
          "redo",
          "|",
          "preview",
        ],
        spellChecker: false,
      })
    })
  }, 100)
})
