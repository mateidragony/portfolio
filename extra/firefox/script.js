'use strict'

const links = {
	'outlook' : ['https://outlook.office.com/mail/'],
	'calendar' : ['https://outlook.office.com/calendar/view/week'],
	'canvas' : ['https://iu.instructure.com/'],
	'onedrive' : ['https://indiana-my.sharepoint.com/my'],
	'github' : ['https://github.com/'],
	'gmail' : ['https://mail.google.com/mail/u/0/#inbox'],
	'house' : ['https://p-auth.duke-energy.com/my-account/dashboard',
			   'https://myaccount.centerpointenergy.com',
			   'https://esuite.bloomington.in.gov/eSuite.Utilities/AccountSummary/',
			   'https://indiana-my.sharepoint.com/:x:/r/personal/mcloteau_iu_edu/_layouts/15/Doc.aspx?sourcedoc=%7B3BE5C5E1-734A-4A0B-823A-955E24B7BCAD%7D&file=Excel-Tactics-Shared-Expense-Calculator-Extended.xlsx'],
	'teams' : ['https://teams.microsoft.com']
}

const buttons = document.querySelectorAll('.quick-links a') 
const keys = new Set()

for (let i = 0; i != buttons.length; ++i) {
	const b = buttons[i]
	const classLinks = links[b.classList[0]]
	if (classLinks.length == 1) {
		b.href = classLinks[0]
	} else {
		b.href = '.'
		b.onclick = () => {
			for (const link of classLinks) {
				window.open(link)
			}
		}
	}
	// const label = document.createElement('p')
	// label.innerHTML = `C-${i+1}`
	// b.appendChild(label)
}

window.onkeyup = (e) => {
	keys.delete(e.key)
}

window.onkeydown = (e) => {
	keys.add(e.key)
	if (keys.has('Control')) {
		for (let i = 0; i != buttons.length; ++i) {
			if (keys.has(`${i+1}`)) {
				buttons[i].focus();
			}
		}
	}
}
