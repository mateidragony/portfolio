async function loadImage(img) {
	await new Promise((resolve, reject) => {
		if (img.complete) {
			resolve()
		} else {
			img.onload = () => resolve()
			img.onerror = () => reject(new Error('Image failed to load'))
		}
	})
}
