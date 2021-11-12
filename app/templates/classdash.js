<script type="text/javascript">
var breakStartTemp = moment.utc('{{break.breakstart}}').toDate();
breakStartTemp = moment(breakStartTemp).local();
console.log(breakStartTemp)
var breakEndTemp = moment(breakStartTemp).add('{{break.breakduration}}', 'minutes');
document.getElementById("in10mins{{loop.index}}").innerHTML = breakEndTemp.format('h:mm:ss a');
if ('{{currUser.role.lower()}}' == "teacher") {
  if (breakEndTemp.isBefore(moment().local()) == false) {
    document.getElementById("isover{{loop.index}}").innerHTML = "On Break";
    document.getElementById("isover{{loop.index}}").style.backgroundColor='#0000ff';
    document.getElementById("isover{{loop.index}}").style.color='#ffffff';
  } else {
    document.getElementById("isover{{loop.index}}").style.backgroundColor='#00ff00';
    document.getElementById("isover{{loop.index}}").innerHTML = "Back to Work";
  }
}
</script>