package main

import (
	"fmt"
	log "github.com/sirupsen/logrus"
	"net"
	"os"
	"regexp"
	"strings"
	"time"
)

var (
	port = os.Getenv("SERVER_PORT")
)

func main() {
	if port=="" {
		port="8080"
		log.Info("using default port "+port)
	}

	l, err := net.Listen("tcp", ":"+port)
	if err != nil {
		fmt.Println("Error listening:", err.Error())
		os.Exit(1)
	}

	defer l.Close()
	fmt.Println("Listening on port: "+port)
	for {
		conn, err := l.Accept()
		if err != nil {
			fmt.Println("Error accepting: ", err.Error())
			os.Exit(1)
		}
		go handleRequest(conn)
	}
}

func handleRequest(conn net.Conn) {
	req:=""
	for  {
		// read tcp connection bytewise
		buf := make([]byte, 1)
		_, err := conn.Read(buf)
		if err != nil {
			// just hackily assuming any error is an EOF
			break
		}
		req+=string(buf)
		if strings.Contains(req,"\r\n\r\n") {
			// break before reading body as we do not need it
			break
		}
	}

	// find URL in plain http request (seems AC is only sending GET or POST requests
	r,_:=regexp.Compile("(GET|POST) (.*?) .*")
	matches:=r.FindStringSubmatch(req)
	if len(matches)!=0 {
		// when we find an URL in the plain http request we fake the response
		url:=matches[2]
		fakeResponse(url,conn)

		// wait a second before trying to read a next request from the same TCP connection from the AC
		// this is the reason we cannot use a normal http server as it closes the TCP connection after responding
		// but the AC reuses the same TCP connection to send other http request after always sending an NTP request first
		time.Sleep(time.Second)
		handleRequest(conn)
	}

	conn.Close()
}

func fakeResponse(url string, conn net.Conn) {
	// plain http response template
	ok:="HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nServer: Microsoft-IIS/8.5\r\nX-Powered-By: PHP/5.4.11\r\nAccess-Control-Allow-Origin: *\r\nDate: %s GMT\\r\\nContent-Length: %d\r\n\r\n%s"
	resp:=""
	log.Infof("got request to %s",url)
	now:=time.Now()

	if strings.Contains(url, "CM=UI_NTP") {
		// wants time gets time
		// format: 'NTP 2022-02-01T13:55:14+00:00 UI SERVER (M.A.V. srl)'
		resp=now.Format("NTP 2006-01-02T15:04:05+00:00 UI SERVER (M.A.V. srl)")
	}else if strings.Contains(url, "CM=UI_FLG") {
		// i don't know what all these fields are for. i did not find any correlation to the rest of the HMI query part
		// but it seems this string as response does always work even though i found different responses from the public IP
		resp="{|1|0|1|0|0|0|N,N,N,N,1,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N,N|}[|0|||]ACN_FREE <br>\t\t"
	} else {
		// probably post, no fucking idea what it tries to do.. send captured response, always is the same
		resp="|}|}\t\t"
	}

	length:=len([]byte(resp))
	// fill plain http response template, we always return a 200
	resp=fmt.Sprintf(ok,now.Format("Mon, 02 Jan 2006 15:04:05"),length,resp)
	log.Infof("responding with: %s",resp)
	conn.Write([]byte(resp))
}
