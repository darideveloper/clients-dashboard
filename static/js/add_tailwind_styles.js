document.addEventListener("DOMContentLoaded", () => {
  const classes = [
    {
      selector: ".btn",
      classes: "bg-primary-600 block border border-transparent cursor-pointer font-medium px-3 py-2 rounded-default text-white w-full lg:w-auto flex items-center justify-center hover:bg-primary-700 hover:text-white transition-colors duration-300",
    },
    {
      selector: ".img-preview",
      classes: "w-auto h-16 rounded-xl object-cover",
    },
  ]
  for (const elem_data of classes) {
    const { selector, classes } = elem_data
    const elems = document.querySelectorAll(selector)
    elems.forEach((elem) => {
      elem.classList.add(...classes.split(" "))
    })
  }
})
