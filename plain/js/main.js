(async () => {
	await initData()

	injectName(document.querySelector('.name'))
	await injectImage(document.querySelector('.headshot'))
	injectBlurb(document.querySelector('.blurb'))

	about.links.push({'link' : `${baseUrl()}/common/resume/resume.html`, 'text' : 'Resume'})	
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
	
	document.querySelector('.loader').classList.add('hidden')
})()
