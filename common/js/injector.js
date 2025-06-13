'use strict'

let about, experience, projects;

function mdLinkToAnchor(str) {
	return str.replaceAll(/\[([^\]^\[]+)\]\(([^\)^\(]+)\)/g, "<a href='$2'>$1</a>")
}


async function getData(name) {
	return fetch(`${window.location.origin}/common/content/${name}.json`)
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

