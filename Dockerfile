FROM golang as builder

WORKDIR /app
COPY . .

RUN go build .

FROM ubuntu

COPY --from=builder /app/ac-dummy .

CMD ["./ac-dummy"]