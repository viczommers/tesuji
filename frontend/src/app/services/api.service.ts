import axios, { AxiosProgressEvent } from 'axios';

const api = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_URL });

type UploadData = {
    name: string;
    age: number;
    email: string;
    password: string;
};

export class APIService {
    static async upload(data: UploadData) {

        const response = await api.post('/upload', data, {
            headers: {
                'Content-Type': 'application/json',
            },
        });
        return response.data;
    }
}