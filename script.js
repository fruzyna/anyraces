/**
 * Ensures there is a leading zero on any single digit datetime values.
 * @param {Number} number Datetime number to pad.
 */
function pad(number)
{
    return number.toString().padStart(2, '0')
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
        // TODO: determine CDT/CST automatically
        let local = new Date(`${now.getFullYear()}/${date.innerText} ${time.innerText} CDT`)

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
            date.innerText = `${pad(local.getMonth() + 1)}/${pad(local.getDate())}`
            time.innerText = `${pad(local.getHours())}:${pad(local.getMinutes())}`
        }

        // highlight races starting within an hour or started within the last 3 hours
        let delta = (now - local) / (1000 * 60 * 60)
        if (delta > -1 && delta < 0)
        {
            el.getElementsByClassName('race')[0].classList.add('next')
        }
        if (delta > 0 && delta < 3)
        {
            el.getElementsByClassName('race')[0].classList.add('live')
        }
    }
}

update_time()
