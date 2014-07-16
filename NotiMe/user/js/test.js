$(document).ready(function(){    
    websocket("localhost","8888","/NotiMe");
});

function websocket(host,port,uri){
	var ws;
	var url = "ws://" + host + ":" + port + uri;

	$("#openWS").click(function(evt){
		evt.preventDefault();
		
		ws = new WebSocket(url);

		ws.onopen = function(evt){ 
			console.log("connection with " + url + " opened");
			$("#consoleDiv").append("<p>connection with " + url + " opened</p>");
		};
     
		ws.onmessage = function(evt){
			console.log("message received: " + evt.data);
			$("#consoleDiv").append("<p>message received: " + evt.data +"</p>");
		};

		ws.onclose = function(evt){
			console.log("connection with " + url + " closed");
			$("#consoleDiv").append("<p>connection with " + url + " closed</p");
		};	
		
		ws.onerror = function(evt){
			console.log("error occured");
		};
	});
	
	$("#sendWS").click(function(evt){
		evt.preventDefault();
		
		var msg = "header:"+$("#hmsg").val()+" | "+ $("#bmsg").val();
		console.log("message to be sent to server: " + msg);
		ws.send(msg);
	});	
}