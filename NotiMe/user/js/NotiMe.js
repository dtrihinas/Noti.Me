$(document).ready(function(){  
	var ws;
    initWebsocket();
    
    $("#opDiv").hide();
    $("#addMetric").click(addMetric);
    $("#addMetricSubmit").click(addMetricSubmit);
    $("#addMetricClear").click(clearVals);
    $("#addMetricHide").click(hideOps);
    $("#removeMetric").click(removeMetric);
    $("#removeMetricSubmit").click(removeMetricSubmit);
    $("#removeMetricClear").click(clearVals);
    $("#removeMetricHide").click(hideOps);
    $("#getConIDSubmit").click(getConIDSubmit);
    $("#sublist").click(sublist);
    $("#sublistSubmit").click(sublistSubmit);
    $("#sublistClear").click(clearVals);
    $("#sublistHide").click(hideOps);
});

function sublist(){
    $("#opDiv").show();
    $(".sl").show();
    $(".am").hide();
	$(".nd").hide();
	$(".rm").hide();
}

function sublistSubmit(){
	var msg = 'header: LIST |'
		+ '{"conID":"' + $("#SLconID").val() +'"}';
	console.log("message to be sent to server: " + msg);
	ws.send(msg);
}

function addMetric(){
    $("#opDiv").show();
    $(".am").show();
	$(".nd").hide();
	$(".rm").hide();
    $(".sl").hide();
}

function addMetricSubmit(){
	var msg = 'header: ADD |'
			+ '{"conID":"' + $("#AMconID").val() +'",'
			+ '"name":"' + $("#AMname").val() +'",'
			+ '"filter":"' + $("#AMfilter").val() +'",'
			+ '"action":"' + $("#AMaction").val() +'",'
			+ '"units":"' + $("#AMunits").val() +'"}';
	console.log("message to be sent to server: " + msg);
	ws.send(msg);
}

function clearVals(){
	$("#AMconID").val("");
	$("#AMname").val("");
	$("#AMfilter").val("");
	$("#AMaction").val("");
	$("#AMunits").val("");
	$("#RMconID").val("");
	$("#RMsubID").val("")
}

function hideOps(){
    $("#opDiv").hide();
}

function removeMetric(){
    $("#opDiv").show();
    $(".rm").show();
	$(".nd").hide();
	$(".am").hide();
    $(".sl").hide();
}

function removeMetricSubmit(){
	var msg = 'header: REMOVE |'
			+ '{"conID":"' + $("#RMconID").val() +'",'
			+ '"subID":"' + $("#RMsubID").val() +'"}';
	console.log("message to be sent to server: " + msg);
	ws.send(msg);
}

function getConIDSubmit(){
	var msg = 'header: CONID | ';
	console.log("message to be sent to server: " + msg);
	ws.send(msg);
}

function initWebsocket(){
	var host = $("#serverIP").val();
	var port = $("#serverPort").val();
	var uri = $("#serverURI").val();
	var url = "ws://" + host + ":" + port + uri;

	$("#openWS").click(function(evt){
		evt.preventDefault();
		
		ws = new WebSocket(url);

		ws.onopen = function(evt){ 
			console.log("connection with " + url + " opened");
			$("#consoleDiv").append("<div id=\"console_row\"> &gt; connection with " + url + " opened</div>");
		};
     
		ws.onmessage = function(evt){
			console.log("message received: " + evt.data);
			$("#consoleDiv").trigger("consoleEvt",{Param1:evt.data});
		};

		ws.onclose = function(evt){
			console.log("connection with " + url + " closed");
			$("#consoleDiv").append("<div id=\"console_row\"> &gt; connection with " + url + " closed</div>");
		};	
		
		ws.onerror = function(evt){
			console.log("error occured");
		};
	});
	
	$("#consoleDiv").bind("consoleEvt", 
			function(e,par){
				var evt=par.Param1;
				
				var len=$("#consoleDiv").children().length;
				if (len > 50)
					$('#consoleDiv').find("div:lt(2)").html("");	
				
				$("#consoleDiv").append("<div id=\"console_row\"> &gt; message received: " + evt +"</div>");
				$("#consoleDiv").animate({ scrollTop: $("#consoleDiv").prop("scrollHeight") - $('#consoleDiv').height() }, 1000);
			}
		);	
}