input.addEventListener("input", async () => {
  const res = await fetch(`/autocomplete?q=${input.value}`)
  const data = await res.json()
  // show dropdown suggestions
})
