/**
 * Hides all table rows that don't match the given tag.
 * @param {string} tag Tag name
 */
function show_tag(tag)
{
    let gray = true
    let elements = document.getElementsByClassName('row')
    for (el of elements)
    {
        if (el.classList.contains(tag) || tag === 'All')
        {
            el.style.visibility = 'visible'
            el.classList.remove('gray')
            if (gray)
            {
                el.classList.add('gray')
            }
            gray = !gray
        }
        else
        {
            el.style.visibility = 'collapse'
        }
    }
}

/**
 * Hides all table rows that have a cell matching the given series.
 * @param {string} series Series tag name 
 */
function show_series(series)
{
    let gray = true
    let elements = document.getElementsByClassName('row')
    for (el of elements)
    {
        let cells = el.getElementsByClassName('series')
        if (cells.length === 1 && cells[0].classList.contains(series) || series === 'All')
        {
            el.style.visibility = 'visible'
            el.classList.remove('gray')
            if (gray)
            {
                el.classList.add('gray')
            }
            gray = !gray
        }
        else
        {
            el.style.visibility = 'collapse'
        }
    }
}

// pull tag and series params from URL
const urlParams = new URLSearchParams(window.location.search)
const tag = urlParams.get('tag')
const series = urlParams.get('series')

// add the series/tag to the title, then hide rows
if (series)
{
    document.getElementById('tag').innerText = series + ' '
    show_series(series)
}
else if (tag)
{
    document.getElementById('tag').innerText = tag + ' '
    show_tag(tag)
}
