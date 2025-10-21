'use strict'

function getPageInfos() {
	return fetch(`${baseUrl()}/pages.json`)
		.then(res => res.text())
		.then(text => JSON.parse(text))
		.catch(err => console.error(err));
}

function injectPages(pageInfos) {
	const pages = document.querySelector('.page-blocks')
	for (const pageInfo of pageInfos) {
		const page = document.createElement('a')
		page.classList.add('page')
		page.href = pageInfo.link
		page.innerHTML = `<div class="img-container">
		  <img src="${baseUrl()}/screenshots/${pageInfo.image}" alt="Screenshot of ${pageInfo.title} page" />
		</div>
		<h3>${pageInfo.title}</h3>
		<p>${pageInfo.description}</p>`
		pages.appendChild(page)
	}
}


(async () => {
	const root = document.documentElement
	
	// inject pages data
	const pages = await getPageInfos()
	injectPages(pages)

	// lucky button
	document.querySelector('.lucky').onclick = () => {
		window.location = pages[Math.floor(Math.random() * pages.length)].link
	}
	
	// color theme dropdown
	let selected
	const themeOptions = document.querySelector('.theme-options')
	const themeButton = document.querySelector('.color-theme button')
	const buttonLabel = document.querySelector('.color-theme button .theme-label')
	themeButton.onclick = () => {
		themeOptions.classList.toggle('show')
		if (themeOptions.classList.contains('show')) themeOptions.style.display = 'flex'
		else setTimeout(() => themeOptions.style.display = 'none', 100)
	}

	window.onclick = (e) => {
		if (!themeButton.contains(e.target) && !themeOptions.contains(e.target) ) {
			themeOptions.classList.remove('show')
			setTimeout(() => themeOptions.style.display = 'none', 100)
		}
	}

	for (const themeLabel of themeOptions.children) {
		themeLabel.onclick = () => {
			const oldBG =  window.getComputedStyle(root).getPropertyValue('--background');
			
			selected.classList.remove('selected')
			root.classList.remove(selected.id)
			
			selected = themeLabel
			selected.classList.add('selected')
			root.classList.add(selected.id)
			
			buttonLabel.innerHTML = selected.innerHTML
			
			themeOptions.classList.remove('show')
			setTimeout(() => themeOptions.style.display = 'none', 100)
			
			document.querySelector('.transition-circle').classList.add('activated')
			document.body.style.backgroundColor = oldBG
			setTimeout(() => {
				document.querySelector('.transition-circle').classList.remove('activated')
				document.body.style.backgroundColor = 'var(--background)'
			}, 500)
		}
	}

	// set default selected color theme
	if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
		const dark = [...themeOptions.children].find(e => e.id === 'dark')
		dark.classList.add('selected')
		buttonLabel.innerHTML = dark.innerHTML
		selected = dark
		root.classList.add('dark')
	} else {
		const light = [...themeOptions.children].find(e => e.id === 'light')
		light.classList.add('selected')
		buttonLabel.innerHTML = light.innerHTML
		selected = light
		root.classList.add('light')
	}
})()

window.onload = () => {
	requestAnimationFrame(() => {
		document.querySelector('.fade-in').classList.add('show')
	})
}



document.querySelector('#test').onclick = async (e) => {
	const shareText = `IDGuess 1 2/6

🔴🔴🔴🔴🔴
🟡🟡🔴⚫🟡
`

	try {
		if (navigator.share) {
			await navigator.share({
				title: "IDGuess",
				url: "www.mateicloteaux.com",
				text: shareText
			});
		} else if (navigator.clipboard) {
			navigator.clipboard.writeText(shareText)
			notify('Copied results to clipboard')
		} else {
			notify('Something went wrong')
		}
	} catch (e) {
		notify('Something went wrong')
		console.error(e)
	}
}
