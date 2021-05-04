const yargs = require('yargs');
const ZwackBLE = require('zwack');
const net = require('net');

const argv = yargs
    .option('host', { alias: 'h', default: 'localhost'})
    .option('port', { alias: 'p', default: 7654})
    .option('quiet', { alias: 'q', default: false})
    .option('name', { alias: 'n', default: 'Viscyc'})
    .option('model-number', { default: 'ZW-101'})
    .option('serial-number', { default: '1'})
    .help()
    .argv;

zwackBLE = new ZwackBLE({
    name: argv.name,
    modelNumber: argv.modelNumber,
    serialNumber: argv.serialNumber,
});


net.createServer(function (socket) {
    socket.on('data', function (data) {
        let received = JSON.parse(data);
        if(!argv.quiet) {
            console.log(received);
        }
        zwackBLE.notifyCSP(received);
    });
}).listen(argv.port, argv.host);
