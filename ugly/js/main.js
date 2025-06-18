'use strict'

async function injectData() {
	injectName(document.querySelector('.name'))
	injectBlurb(document.querySelector('.blurb'))

	about.links.push({'link' : `${baseUrl()}/common/resume/resume.html`, 'text' : 'Resume (page)'})
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
	constructor(x, y, img) {
		this.x = x
		this.y = y
		this.img = img
		this.dx = Math.floor((Math.random() * 5 + 3)) * (Math.random() > 0.5 ? 1 : -1)
		this.dy = Math.floor((Math.random() * 5 + 3)) * (Math.random() > 0.5 ? 1 : -1)
	}

	draw(g) {
		g.drawImage(this.img, this.x, this.y)
	}
}


function splitSpaceSpan(text) {
	const splts = text.split(' ')
	let skipping = false
	for (let i=0; i!=splts.length; ++i) {
		const word = splts[i]
		if (word.includes('<a')) skipping = true
		if (word.includes('</a')) skipping = false
		else if (!skipping) {
			splts[i] = `<span class="word-grow">${word}</span>`
		}
	}
	return splts.join(' ')
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
	
	document.querySelector('.loader').classList.add('hidden')
})()
