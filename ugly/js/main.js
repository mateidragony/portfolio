'use strict'

let firstClick = true

async function injectData() {
	injectName(document.querySelector('.name'))
	injectBlurb(document.querySelector('.blurb'))

	about.links.push({'link' : `${baseUrl()}/common/resume/resume.html`, 'text' : 'Resume (html)'})
	about.links.push({'link' : `${baseUrl()}/common/resume/resume.pdf`, 'text' : 'Resume (pdf)'})	
	injectLinks(document.querySelector('.links'))
	
	injectProjects(document.querySelector('.projects'))

	const projectButton = document.createElement('button')
	projectButton.innerText = 'See more'
	projectButton.onclick = () => {
		document.querySelectorAll('.project.toggle').forEach(p => p.classList.toggle('hidden'))
		projectButton.innerText = projectButton.innerText == 'See more' ? 'See less' : 'See more'
	}
	document.querySelector('.projects').appendChild(projectButton)
	
	injectExperience(document.querySelector('.experience'))
}

class MovingImage {
	constructor(x, y, img, w=undefined, h=undefined) {
		this.x = x
		this.y = y
		if (w == undefined) this.w = Math.random() * 100 + 70
		else                this.w = w
		if (h == undefined) this.h = Math.random() * 100 + 70
		else                this.h = h
		this.img = img
		this.dx = Math.floor((Math.random() * 5 + 3)) * (Math.random() > 0.5 ? 1 : -1)
		this.dy = Math.floor((Math.random() * 5 + 3)) * (Math.random() > 0.5 ? 1 : -1)
	}

	draw(g) {
		g.drawImage(this.img, this.x, this.y, this.w, this.h)
	}

	update(cw, ch) {
		this.x += this.dx
		this.y += this.dy

		if (this.x < 0) {
			this.x = 0
			this.dx *= -1
		} if (this.y < 0) {
			this.y = 0
			this.dy *= -1
		} if (this.x + this.w > cw) {
			this.x = cw - this.w
			this.dx *= -1
		} if (this.y + this.h > ch) {
			this.y = ch - this.h
			this.dy *= -1
		}
	}

	pointCollides(x, y) {
		return x >= this.x && x <= this.x + this.w && y >= this.y && y <= this.y + this.h
	}
}


function splitSpaceSpan(text) {
	const splts = text.split(' ')
	let skipping = false
	for (let i=0; i!=splts.length; ++i) {
		const word = splts[i]
		if (word.includes('<a') || word.includes('<span')) skipping = true
		if (word.includes('</a') || word.includes<'</span') skipping = false
		else if (!skipping) {
			splts[i] = `<span class="word-grow">${word}</span>`
		}
	}
	return splts.join(' ')
}

function randomDictValue(dict) {
	return Object.values(dict)[Math.floor(Math.random() * Object.keys(dict).length)]
}

function resizeCanvas(canvas) {
	canvas.width = window.innerWidth
	canvas.height = window.innerHeight
}

function createImage(src) {
	const img = new Image(100,100)
	img.src = src
	return img
}

function generateMovingImages(movingImages, images) {
	setTimeout(() => {
		movingImages.push(new MovingImage(Math.random() * window.innerWidth,
										  Math.random() * window.innerHeight,
										  randomDictValue(images)))
		generateMovingImages(movingImages, images)
	}, Math.random() * 7000 + 3000)
}


(async () => {
	await initData()
	await injectData()

	let hue = 10
	const main = document.querySelector('main')
	setInterval(() => main.style.backgroundColor = `hsl(${hue+=10}, 100%, 70%)`, 100)


	const name = document.querySelector('.name-container')
	name.onmousemove = (e) => {
		const rect = name.getBoundingClientRect()
		let x = (e.clientX - rect.left) - rect.width / 2
		name.querySelector('h1').style.transform = `rotateZ(${x/10}deg)`
	}

	document.querySelectorAll('p').forEach(e => e.innerHTML = splitSpaceSpan(e.innerHTML))
	document.querySelectorAll('li').forEach(e => e.innerHTML = splitSpaceSpan(e.innerHTML))

	document.querySelectorAll('a').forEach(e => {
		e.onmouseenter = () => {
			e.oldHTML = e.innerHTML
			e.innerHTML = 'CLICK ME NOW!!!'
		}
		e.onmouseleave = () => {
			e.innerHTML = e.oldHTML
		}
	})

	const canvas = document.querySelector('canvas')
	resizeCanvas(canvas)
	const g = canvas.getContext('2d')
	window.onresize = () => {
		if (canvas.width == window.innerWidth && mobileAndTabletCheck());
		else resizeCanvas(canvas)
	}

	const images = {
		'me'            : createImage(`${baseUrl()}/common/assets/me.jpg`),
		'me-ids'        : createImage(`${baseUrl()}/common/assets/me-ids.jpeg`),
		'me-friends'    : createImage(`${baseUrl()}/common/assets/me-friends.JPG`),
		'me-sign'       : createImage(`${baseUrl()}/common/assets/me-sign.jpg`),
		'me-glasses'    : createImage(`${baseUrl()}/common/assets/me-glasses.JPG`),
		'me-snow'       : createImage(`${baseUrl()}/common/assets/me-snow.jpg`),
		'click-go-away' : createImage(`${baseUrl()}/common/assets/click-go-away.png`),
		'look-here'     : createImage(`${baseUrl()}/common/assets/look-here.png`),
		'over-here'     : createImage(`${baseUrl()}/common/assets/over-here.png`),
		'distraction'   : createImage(`${baseUrl()}/common/assets/distraction.png`),
		'dont-misclick' : createImage(`${baseUrl()}/common/assets/dont-misclick.png`),
		'look-at-me'    : createImage(`${baseUrl()}/common/assets/look-at-me.png`),
		'dariana'       : createImage(`${baseUrl()}/common/assets/dariana.jpeg`),
	}
	await Promise.all(Object.values(images).map(i => loadImage(i)))
	const movingImages = [new MovingImage(window.innerWidth/2.1, window.innerHeight/2.3,
										  images['click-go-away'], 200, 200)]

	window.onclick = (e) => {
		let x = e.clientX
		let y = e.clientY

		const collisions = movingImages.filter(i => i.pointCollides(x, y))
		if (collisions.length == 0) {
			if (e.target.tagName == 'A' || e.target.tagName == 'BUTTON') {
				return
			} else if (firstClick) {
				firstClick = false
				movingImages.push(new MovingImage(x, y, images['dont-misclick'], 200, 200))
			} else {
				movingImages.push(new MovingImage(x, y, randomDictValue(images)))
			}
		} else {
			collisions.forEach(c => movingImages.splice(movingImages.indexOf(c), 1))
		}
	}
	
	let allowImages = true
	const stop = document.querySelector('.stop-button')
	stop.onclick = () => {
		allowImages = !allowImages
		stop.innerHTML = stop.innerHTML == 'STOP IMAGES PLEASE!!!' ? 'Bring the images back now!!' : 'STOP IMAGES PLEASE!!!'
	}
	
	document.querySelector('.loader').classList.add('hidden')

	setInterval(() => {
		g.clearRect(0, 0, canvas.width, canvas.height)
		if (!allowImages || mobileAndTabletCheck()) movingImages.splice(0, movingImages.length)
		movingImages.forEach(i => {
			i.update(canvas.width, canvas.height)
			i.draw(g)
		})
	}, 1000/30)
	
	setTimeout(() => generateMovingImages(movingImages, images), 0)
})()
