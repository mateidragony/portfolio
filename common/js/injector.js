'use strict'

let about, experience, projects;

function mdLinkToAnchor(str) {
	return str.replaceAll(/\[([^\]^\[]+)\]\(([^\)^\(]+)\)/g, "<a href='$2' target='_blank'>$1</a>")
}

async function getData(name) {
	return fetch(`${baseUrl()}/common/content/${name}.json`)
		.then(res => res.text())
		.then(data => mdLinkToAnchor(data))
		.then(text => JSON.parse(text))
		.catch(err => console.error(err));
}

async function initData(){
	about = await getData('about')
	experience = await getData('experience')
	projects = await getData('projects')
}


function injectName(html) {
	html.innerHTML = about.name
}

function injectBlurb(html) {
	html.innerHTML = about.blurb
}

async function injectImage(img) {
	img.src = `${baseUrl()}/common/assets/${about.image}`
	img.alt = about.image_alt
	await loadImage(img)
	document.querySelector('.blurb').innerHTML = about.blurb
}

function injectLinks(html) {
	for (let link of about.links) {
		const linkHTML = document.createElement('a')
		linkHTML.classList.add('link')
		linkHTML.href = link.link
		linkHTML.innerText = link.text
		html.appendChild(linkHTML)
	}
}

function injectProjects(html) {
	let i = 0;
	for (let project of projects) {
		const projectHTML = document.createElement('div')
		projectHTML.classList.add('project')
		if (++i > 3) {
			projectHTML.classList.add('toggle')
			projectHTML.classList.add('hidden')
		}
		
		const title = document.createElement('h3')
		title.innerText = project.name
		projectHTML.appendChild(title)

		const links = document.createElement('p')
		links.classList.add('links')
		if (project.link != "") {
			links.innerHTML = `(<a href="${project.link}" target="_blank">link</a>, <a href="${project.source}" target="_blank">source</a>)`
		} else {
			links.innerHTML = `(<a href="${project.source}" target="_blank">source</a>)`
		}
		projectHTML.appendChild(links)
		
		const bullets = document.createElement('ul')
		for (let bullet of project.bullets) {
			const li = document.createElement('li')
			li.innerHTML = bullet
			bullets.appendChild(li)
		}
		projectHTML.appendChild(bullets)

		html.appendChild(projectHTML)
	}
}


function injectExperience(html) {
	for (let exp of experience) {
		const expHTML = document.createElement('div')
		
		const title = document.createElement('h3')
		title.innerText = exp.company
		expHTML.appendChild(title)

		const bullets = document.createElement('ul')
		for (let bullet of exp.bullets) {
			const li = document.createElement('li')
			li.innerHTML = bullet
			bullets.appendChild(li)
		}
		expHTML.appendChild(bullets)
		
		html.appendChild(expHTML)
	}
}
