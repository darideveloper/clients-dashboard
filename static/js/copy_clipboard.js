// clipboard_handler.js
document.addEventListener('DOMContentLoaded', () => {
  const getCookie = (name) => {
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) {
      let cookieValue = decodeURIComponent(parts.pop().split(';').shift())
      // Remove surrounding quotes if they exist
      return cookieValue.replace(/^"|"$/g, '')
    }
  }

  const url = getCookie('copy_to_clipboard')
  if (url) {
    navigator.clipboard.writeText(url).then(() => {
      // Clear the cookie
      document.cookie = "copy_to_clipboard=; path=/; Max-Age=-99999999;"
    })
  }
})
