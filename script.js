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


/**
 * Updates the times to the current timezone and highlights live races.
 */
function update_time()
{
    let update_time
    let now = new Date()
    let elements = document.getElementsByClassName('row')
    for (el of elements)
    {
        // read time from table
        let date = el.getElementsByClassName('date')[0]
        let time = el.getElementsByClassName('time')[0]
        let local = new Date(`${now.getFullYear()}/${date.innerText} ${time.innerText} CST`)

        // determine if local time matches server time zone
        if (update_time === undefined)
        {
            let server = new Date(`${now.getFullYear()}/${date.innerText} ${time.innerText}`)
            update_time = local - server !== 0
            document.getElementById('disclaimer').style.display = 'none'
        }
        // update time if timezone differs
        if (update_time)
        {
            date.innerText = `${local.getMonth()}/${local.getDate()}`
            time.innerText = `${local.getHours()}:${local.getMinutes().padStart(2, '0')}`
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

update_time()
