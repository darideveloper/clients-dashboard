document.addEventListener("DOMContentLoaded", function () {
  const texts = [
    { names: ["created_at_from", "updated_at_from"], text: "Desde" },
    { names: ["created_at_to", "updated_at_to"], text: "Hasta" },
  ]

  texts.forEach((text) => {
    text.names.forEach((name) => {
      const elem = document.querySelector(`[name="${name}"]`)
      if (!elem) return
      elem.placeholder = text.text
    })
  })
})
