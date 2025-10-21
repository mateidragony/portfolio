(async () => {
	await initData()

	injectName(document.querySelector('.name'))
	await injectImage(document.querySelector('.headshot'))
	injectBlurb(document.querySelector('.blurb'))

	about.links.push({'link' : `${baseUrl()}/extra/resume/resume.html`, 'text' : 'Resume (html)'})
	about.links.push({'link' : `${baseUrl()}/extra/resume/MateiCloteauxResume.pdf`, 'text' : 'Resume (pdf)'})	

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


document.querySelector('#test').onclick = async (e) => {
	const shareText = `IDGuess 1 2/6

🔴🔴🔴🔴🔴
🟡🟡🔴⚫🟡`

	try {
		if (navigator.share) {
			await navigator.share({
				title: "IDGuess",
				url: "www.mateicloteaux.com",
				text: shareText
			});
		} else if (navigator.clipboard) {
			navigator.clipboard.writeText(shareText)
		} else {
		}
	} catch (e) {
		console.error(e)
	}
}
