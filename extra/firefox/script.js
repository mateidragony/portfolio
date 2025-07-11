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

for (const b of document.querySelectorAll('.quick-links button')) {
	b.onclick = () => {
		const classLinks = links[b.classList[0]]
		if (classLinks.length == 1) {
			window.location.href = classLinks[0]
		} else {
			for (const link of classLinks) {
				window.open(link)
			}
		}
	}
}

// Titles logic
const numTitles = 4
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    // dark mode
	document.querySelector('.title').src = `titles/dark/${Math.floor(Math.random() * numTitles)}.gif`
} else {
	// light mode
	document.querySelector('.title').src = `titles/light/${Math.floor(Math.random() * numTitles)}.gif`
}
