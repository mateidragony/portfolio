'use strict'

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

function baseUrl() {
	if (window.location.origin == 'https://mateidragony.github.io') {
		return 'https://mateidragony.github.io/portfolio'
	} else {
		return window.location.origin
	} 
}
